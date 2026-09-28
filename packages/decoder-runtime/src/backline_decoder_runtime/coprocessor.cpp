// Backline native slot: value(u64), decoder_id(u32), seq(u32).
// 1/2/3: begin/append/finish. Pipeline finish carries shot ID; 4 collects it.
#include <condition_variable>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <deque>
#include <map>
#include <mutex>
#include <thread>
#include <vector>

namespace {
using Decode = int (*)(const void *, std::size_t);
std::mutex mutex;
std::condition_variable changed;
Decode decode = nullptr;
std::vector<unsigned char> pending;
std::size_t expected = 0;
constexpr std::size_t max_request = 4096;
struct Job { std::uint64_t id; std::vector<unsigned char> data; };
std::deque<Job> jobs;
// Includes queued, executing and completed-but-uncollected requests.
std::map<std::uint64_t, int> results;
std::thread worker;
std::size_t capacity = 0;
std::uint64_t next_id = 0;
bool stopping = false;
std::atomic<bool> timing{false};
std::atomic<std::uint64_t> collect_wait_ns{0};
void clear_request() { pending.clear(); expected = 0; }
void work() {
    std::unique_lock<std::mutex> lock(mutex);
    for (;;) {
        changed.wait(lock, [] { return stopping || !jobs.empty(); });
        if (jobs.empty() && stopping) return;
        Job job = std::move(jobs.front());
        jobs.pop_front();
        Decode fn = decode;
        lock.unlock(); // Neither transport nor collection holds up inference.
        int prediction = -1;
        try { prediction = fn(job.data.data(), job.data.size()); } catch (...) {}
        lock.lock();
        results[job.id] = prediction;
        changed.notify_all();
    }
}
}

extern "C" void evodecode_enable_timing(bool enabled) { timing = enabled; collect_wait_ns = 0; }
extern "C" std::uint64_t evodecode_take_wait_ns() { return collect_wait_ns.exchange(0); }

// Host-side lifecycle calls; stop drains queued jobs before releasing the callback.
extern "C" int evodecode_start_pipeline(std::size_t limit) {
    std::lock_guard<std::mutex> guard(mutex);
    if (!decode || worker.joinable() || limit == 0 || limit > 256) return 1;
    clear_request();
    results.clear();
    jobs.clear();
    capacity = limit;
    next_id = 0;
    stopping = false;
    try { worker = std::thread(work); }
    catch (...) { capacity = 0; return 1; }
    return 0;
}

extern "C" void evodecode_stop_pipeline() {
    {
        std::lock_guard<std::mutex> guard(mutex);
        stopping = true;
        changed.notify_all();
    }
    if (worker.joinable()) worker.join();
    std::lock_guard<std::mutex> guard(mutex);
    capacity = 0;
    results.clear();
    jobs.clear();
    clear_request();
}

extern "C" void evodecode_set_callback(Decode callback) {
    evodecode_stop_pipeline();
    std::lock_guard<std::mutex> guard(mutex);
    decode = callback;
}

extern "C" std::size_t evodecode_coprocessor(
    const void *in, std::size_t in_len, void *out, std::size_t out_cap, void *) {
    std::unique_lock<std::mutex> lock(mutex);
    if (!out || out_cap < 8) return 0;
    unsigned char reply[8] = {0, 1, 0, 0, 0, 0, 0, 0};
    std::uint32_t id = 0;
    if (in && in_len == 16 && decode) {
        std::memcpy(&id, static_cast<const char *>(in) + 8, 4);
        const auto *data = static_cast<const unsigned char *>(in);
        if (id == 1) {
            clear_request();
            std::uint32_t length = 0, version = 0;
            std::memcpy(&length, data, 4);
            std::memcpy(&version, data + 4, 4);
            if ((length > 8 || (capacity && length == 8)) && length <= max_request && version == 1) {
                expected = length;
                pending.reserve((expected + 7) / 8 * 8);
                reply[1] = 0;
            }
        } else if (id == 2) {
            if (expected && pending.size() < expected) {
                pending.insert(pending.end(), data, data + 8);
                reply[1] = 0;
            } else clear_request();
        } else if (id == 4 && capacity) {
            std::uint64_t shot = 0;
            std::memcpy(&shot, data, 8);
            if (results.count(shot)) {
                const auto started = timing ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point{};
                changed.wait(lock, [shot] { return stopping || results.at(shot) != -2; });
                if (timing) collect_wait_ns += std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now() - started).count();
                const int prediction = results.at(shot);
                if (prediction == 0 || prediction == 1) {
                    reply[0] = static_cast<unsigned char>(prediction);
                    reply[1] = 0;
                } else reply[1] = 2;
                results.erase(shot);
            }
        } else if (id == 0 || id == 3) {
            bool valid = id == 0 && !capacity;
            if (id == 3 && expected && pending.size() == (expected + 7) / 8 * 8) {
                valid = true;
                for (auto i = expected; i < pending.size(); ++i) valid &= pending[i] == 0;
            }
            if (valid && capacity) {
                std::uint64_t shot = 0;
                std::memcpy(&shot, data, 8);
                if (!stopping && shot == next_id && results.size() < capacity) {
                    pending.resize(expected);
                    jobs.push_back({shot, std::move(pending)});
                    results.emplace(shot, -2);
                    ++next_id;
                    reply[1] = 0; // Submission acknowledgement, not a prediction.
                    changed.notify_all();
                } else reply[1] = 3; // Full queue or invalid shot sequence.
            } else if (valid) {
                const int prediction = id == 0 ? decode(in, 8) : decode(pending.data(), expected);
                if (prediction == 0 || prediction == 1) {
                    reply[0] = static_cast<unsigned char>(prediction);
                    reply[1] = 0;
                } else reply[1] = 2;
            }
            clear_request();
        } else clear_request();
    }
    std::memcpy(out, reply, 8);
    return 8;
}
