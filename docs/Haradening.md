**Hardening and Optimization Plan for tzMCP Media Proxy**

This plan outlines a step-by-step strategy to harden the security and improve the performance of the tzMCP proxy tool, with an emphasis on stability and safe, incremental progress.

---

### **Phase 1: Hardening and Stability (Security-First)**

#### **Step 1: Lock Down Dangerous Behaviors**

* [x] Disable or eliminate all "trusted pipeline" shortcuts.
* [x] Sanitize and validate all config inputs.
* [x] Escape or reject unsafe characters in filenames/URLs.
* [x] Validate MIME types and enforce strict extension whitelist.

#### **Step 2: Improve Logging Transparency**

* [x] Ensure all rejection reasons are clearly logged.
* [x] Allow export of logs for user debugging.
* [ ] Add log filtering (e.g., show only errors/skips/saves).

#### **Step 3: Enhance Config Monitoring**

* [x] Migrate config watcher to `watchdog`.
* [x] Avoid excessive polling or reloads.
* [x] Add a small debounce buffer (e.g., 250ms) to coalesce edits.

#### **Step 4: Guard Against Path Traversals / Write Abuse**

* [x] Normalize and resolve `save_dir`.
* [x] Reject paths that escape the project root or cache directory.

#### **Step 5: Test Invalid/Malicious Payloads**

* [ ] Attempt malformed URLs, headers, etc.
* [ ] Verify that oversized and untrusted binary blobs are rejected.
* [x] Confirm that malicious filenames (e.g., "../", unicode tricks) don’t escape.

---

### **Phase 2: Bottleneck Identification**

#### **Step 6: Instrument Key Functions**

* [ ] Add timing logs to all major processing steps:

  * MIME sniffing
  * Extension check
  * File size check
  * Image size (PIL) check
* [ ] Add global "response total time" log.

#### **Step 7: Analyze Logs with Real Usage**

* [ ] Load pages with 50-100 images.
* [ ] Measure average time per check.
* [ ] Graph or tally function durations.
* [ ] Identify slowest consistent operation (likely image parsing).

#### **Step 8: Triage Slowness Causes**

* [ ] Try toggling config options (e.g., disable pixel filter).
* [ ] Compare image file size vs. pixel size cost.
* [ ] Attempt caching repeated URLs.

---

### **Phase 3: Performance Optimizations (Safe Path)**

#### **Step 9: Prioritize Early Rejection**

* [ ] Move fast checks (file size, extension, blacklist) to top.
* [ ] Reorder filters by average cost.

#### **Step 10: Optional Caching Layer**

* [ ] Memoize seen URLs + their pass/fail result.  (NO)
* [ ] Timebox cache expiration (5 min).
* [ ] Ensure thread-safe access if multithreaded.

#### **Step 11: Prepare for Concurrency**

* [ ] Identify thread-safe points in `response()`.
* [ ] Break processing into isolated units (image validation, file write, etc).
* [ ] Wrap CPU-bound tasks (like PIL image parsing) with `concurrent.futures.ThreadPoolExecutor`.
* [ ] Limit to 2-4 concurrent threads max (initial).

#### **Step 12: Profile With Threads Enabled**

* [ ] Re-run timing logs with concurrency on.
* [ ] Measure speedup, I/O contention.
* [ ] Catch and report exceptions cleanly from threads.

---

### **Phase 4: Cleanup and Documentation**

#### **Step 13: Final Audit**

* [ ] Recheck hardening protections.
* [ ] Confirm log clarity and usefulness.
* [ ] Stress-test long sessions or image-heavy pages.

#### **Step 14: Document Advanced Options Safely**

* [ ] Clearly label any performance-enhancing but riskier flags.
* [ ] Add tooltips or config guide for all UI settings.

#### **Step 15: Version Lock and Release**

* [ ] Freeze dependencies.
* [ ] Create tagged release branch.
* [ ] Push documentation for end users and contributors.

---

**NOTE:** All optimization steps should be disabled by default unless verified safe. Users should not need to understand concurrency or I/O performance to benefit from safe defaults.
