# Test Cases — Network Path and Delay Analyzer

## Test Case 1: Valid Domain — google.com
- **Input**: `google.com`, Method: ICMP, Max Hops: 30
- **Expected**: 
  - Resolves to a valid IP (e.g., 142.250.x.x)
  - Multiple hops displayed (typically 8-15)
  - RTT values shown for most hops
  - Geolocation data appears (Google data centers)
  - Map shows markers with polyline path
  - Chart shows RTT bars
  - Bottleneck analysis identifies highest-delay hop
  - Ping statistics show low loss (<5%)
  - Analysis saved to history

## Test Case 2: Invalid Domain — thisdomaindoesnotexist12345.xyz
- **Input**: `thisdomaindoesnotexist12345.xyz`, Method: ICMP
- **Expected**:
  - Error message displayed: "Unable to resolve host" or similar
  - No hops in table
  - Progress bar stops and shows error state
  - No crash; UI remains functional
  - User can immediately start a new trace

## Test Case 3: Private IP — 192.168.1.1
- **Input**: `192.168.1.1`, Method: ICMP
- **Expected**:
  - Request blocked with clear error message: "Target is a private/reserved IP address"
  - No traceroute executed (security measure)
  - SSRF prevention working correctly

## Test Case 4: Unreachable Host — 198.51.100.1 (TEST-NET-2, non-routable)
- **Input**: `198.51.100.1`, Method: ICMP, Max Hops: 15, Timeout: 2
- **Expected**:
  - First few hops may respond with RTTs
  - Later hops show `*` (timeout)
  - Traceroute completes after reaching max_hops
  - Packet loss high (many * * * lines)
  - Analysis notes "Route did not reach destination"
  - Partial geolocation for responding hops

## Test Case 5: IPv6 Address — 2001:4860:4860::8888 (Google Public DNS)
- **Input**: `2001:4860:4860::8888`, Method: ICMP
- **Expected** (on IPv6-enabled network):
  - IPv6 traceroute executed (traceroute6 or tracert -6 on Windows)
  - Hops show IPv6 addresses
  - Geolocation works for public IPv6 addresses
  - Map and chart render correctly
- **Expected** (on IPv4-only network):
  - Graceful error: "IPv6 not available" or traceroute fails with clear message
  - No crash; UI shows error state

---

## Screenshots Checklist

- [ ] Home page with empty input form (light mode)
- [ ] Home page (dark mode)
- [ ] Trace in progress (streaming hops appearing)
- [ ] Completed trace: hop table with color-coded latency
- [ ] RTT bar chart
- [ ] Interactive map with route markers and polyline
- [ ] Bottleneck analysis and ping stats cards
- [ ] History page with saved analyses
- [ ] About page showing networking concepts
- [ ] Mobile view (responsive layout)
- [ ] Error state (invalid domain)
- [ ] Error state (private IP blocked)
