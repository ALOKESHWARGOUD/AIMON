# AIMON — Use Cases

## 1. EdTech Leak Monitoring

**Problem:** Online course platforms lose revenue when paid courses are leaked to
Telegram channels, torrent sites, and cloud storage mirrors.

**AIMON Solution:**
- DiscoveryModule searches for brand + "free download", "leaked", "torrent"
- TelegramDiscoveryModule scans public channels for course content
- NetworkMapperModule maps relationships between mirror sites
- RiskEngineModule scores each source by leak probability

**Example:**
```python
async with AIMON() as fw:
    report = await fw.monitor.brand("YourPlatformName")
    if report.risk_level == "confirmed":
        # Trigger DMCA takedown workflow
        pass
```

---

## 2. Media and Streaming Piracy Detection

**Problem:** Studios and streaming services need early detection of leaked
movies, episodes, and trailers before they go viral.

**AIMON Solution:**
- FingerprintEngine creates perceptual hashes of original content
- VerificationModule compares discovered content against registered fingerprints
- AlertsModule fires high-priority alerts when a fingerprint match exceeds threshold

**Optional extra required:**
```bash
pip install "aimon-framework[fingerprint]"
```

---

## 3. SaaS Intellectual Property Monitoring

**Problem:** SaaS companies need to detect leaked training materials,
internal documentation, API credentials, and product roadmaps.

**AIMON Solution:**
- DiscoveryModule monitors GitHub, Pastebin, Reddit, and forums
- LeakSignalModule detects credential patterns, internal URL patterns, and
  confidential keyword density
- NetworkMapperModule maps how leaked documents spread across platforms

---

## 4. Open Source Brand Monitoring

**Problem:** Open-source projects need to detect counterfeit packages,
typosquatting, and impersonation on PyPI, npm, and GitHub.

**AIMON Solution:**
- Custom connector targeting PyPI/npm APIs
- IntelligenceModule classifies similarity to original package metadata
- AlertsModule triggers webhook notifications to maintainers

---

## 5. Corporate Data Leak Detection

**Problem:** Enterprises need to detect proprietary data appearing on
dark web forums, public paste sites, and social platforms.

**AIMON Solution:**
- Multi-connector discovery (Google, Reddit, custom dark web connectors)
- RiskEngineModule scores based on data sensitivity signals
- Neo4j storage for graph-based analysis of leak propagation networks

**Optional extra required:**
```bash
pip install "aimon-framework[neo4j]"
```
