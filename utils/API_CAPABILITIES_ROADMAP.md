# ActronAir Neo Integration - API Capabilities & Enhancement Roadmap

**Date**: June 2026
**Status**: Stable (MQTT support fully operational)
**Audience**: Developers, Maintainers, Integration Users

---

## What's Currently Exposed & Working

### ✅ Core Functionality (100% Complete)

- **Climate Control**
  - Mode control: COOL, HEAT, AUTO, FAN, OFF
  - Fan modes: LOW, MED, HIGH, AUTO (where supported)
  - Temperature setpoint control (separate cool/heat targets)
  - Turbo mode (Advance/Aires series)
  - Quiet mode (Advance/Aires series)
  - Away mode
  - Continuous fan mode

- **Zone Management**
  - Enable/disable zones
  - Zone temperature setpoint control
  - Zone humidity monitoring
  - Zone damper position (where available)
  - Zone battery level and signal strength
  - Zone presets (save/restore configurations)

- **System Monitoring**
  - Indoor/outdoor temperature
  - Indoor/outdoor humidity
  - Compressor capacity and state
  - WiFi signal strength and connection info
  - Filter status
  - System uptime and firmware versions
  - Defrost mode status

- **Real-time Updates (MQTT)**
  - Full status snapshots
  - Incremental state changes
  - Command response acknowledgments
  - 60-second heartbeat monitoring
  - Automatic fallback to polling if MQTT fails

### ⚠️ Conditionally Supported (Platform-Dependent)

| Feature                 | Classic    | Advance | Aires | Status                               |
| ----------------------- | ---------- | ------- | ----- | ------------------------------------ |
| Outdoor temperature     | ❌         | ✅      | ✅    | Gracefully absent on Classic         |
| AUTO fan mode           | ❌         | ✅      | ✅    | Disabled UI control when unavailable |
| Turbo mode              | ❌         | ✅      | ✅    | Gracefully hidden when unsupported   |
| Quiet mode              | ❌         | ✅      | ✅    | Gracefully hidden when unsupported   |
| Dry mode                | ❌         | ✅      | ✅    | Gracefully hidden when unsupported   |
| VFT (Variable Fan Tech) | ❌         | ✅      | ✅    | Displayed when available             |
| Zone damper position    | ⚠️ Limited | ✅      | ✅    | May be unavailable on some systems   |

### ❌ Known Missing / Not Implemented

| Feature                   | Platform       | Impact                                  | Priority |
| ------------------------- | -------------- | --------------------------------------- | -------- |
| **Que/NX-Gen Support**    | Que            | Can't control any Que systems           | High     |
| **ACM-2 Support**         | Actron Connect | Can't control ACM-2 systems             | High     |
| **SignalR/SSE Transport** | Que            | MQTT not available for Que              | High     |
| **Event History**         | All            | Actron disabled (July 2025)             | Low      |
| **User Account Info**     | All            | No account management                   | Low      |
| **Batch Commands**        | All            | Can't send multiple commands atomically | Medium   |
| **Webhook Support**       | All            | Unknown if available                    | Unknown  |
| **System Configuration**  | All            | Can't modify WiFi/settings              | Medium   |

---

## API Endpoints Reference

### Currently Used

```python
# Authentication
POST /api/v0/oauth/token
  - Device code flow (RFC 8628)
  - Token refresh
  - Token expiration handling

# System Discovery
GET /api/v0/client/ac-systems?includeNeo=true
  - List all user's AC systems
  - Filter for Neo vs Que systems

# Status Polling
GET /api/v0/client/ac-systems/status/latest?serial={serial}
  - Complete system status
  - Cached for 15 seconds
  - Circuit breaker for health management

# Real-time Connection
GET /api/v0/messaging/connection/details
  - MQTT broker discovery
  - Authentication credentials
  - Topic structure information

# Control Commands
POST /api/v0/client/ac-systems/cmds/send
  - Set mode, fan mode, setpoint
  - Enable/disable zones
  - Control special modes
  - Rate limited: 20 requests/minute
```

### Potentially Available (Not Used)

```python
# Account Information
GET /api/v0/client/account
  - User profile
  - Account settings
  - Subscription info
  - NOT used in current integration

# Event History (DEPRECATED)
GET /api/v0/client/events/*
  - Event timeline
  - Audit log
  - DISABLED by Actron (July 2025)
  - NO longer available
```

### Unknown / Not Researched

```
# Possible batch commands endpoint
POST /api/v0/client/ac-systems/cmds/batch

# Possible system configuration endpoint
POST /api/v0/client/ac-systems/config

# Possible account management endpoint
PATCH /api/v0/client/account

# Que platform equivalents
/api/v0/  (on que.actronair.com.au)
```

---

## Platform Support Matrix

```
┌─────────────────────────────────────────────────────────────┐
│            Current vs. Needed Platform Support              │
├──────────┬─────────────┬──────────────┬──────────────────────┤
│ Platform │ Integration │ Que Platform │ ACM-2 Platform      │
├──────────┼─────────────┼──────────────┼──────────────────────┤
│ Status   │ ✅ Working  │ ❌ Missing   │ ❌ Unknown/Missing   │
│ Coverage │ 100%        │ 0%           │ 0%                   │
│ Users    │ ~95%        │ ~5%          │ <1% (emerging)       │
│ Priority │ Maintain    │ Add Support  │ Research + Plan      │
│ Effort   │ Low         │ High         │ Very High            │
│ Timeline │ Ongoing     │ 2-3 months   │ Q3-Q4 2026           │
└──────────┴─────────────┴──────────────┴──────────────────────┘
```

---

## What Data Fields Are Exposed

### Complete Extraction

The integration successfully extracts and exposes **100+ data points** per system:

**AC System Level** (25+ fields):

- Power state, mode, fan mode, setpoints
- Compressor state, capacity, speed
- WiFi signal, channel, firmware
- Filter status, defrost mode
- Model, serial, firmware versions
- Away mode, quiet mode, turbo mode state
- Cloud connection health metrics

**Zone Level** (15+ fields per zone):

- Temperature, humidity, setpoint
- Enable/disable state
- Damper position
- Battery level, signal strength
- Last connection time, connection state
- Zone capabilities
- Airflow control (where available)

**System Level** (20+ fields):

- WiFi SSID, channel, quality
- System uptime
- Cloud connection status
- Packet counters, error counters
- Board temperature
- VFT state and airflow

### Conditional/Missing Fields

**Classic Series Gaps**:

- Outdoor temperature (returns fake 3000.0°C)
- AUTO fan mode (unavailable)
- Turbo/Quiet/Dry modes (unsupported)
- Variable fan technology

**Que/NX-Gen Systems**:

- Everything (platform not supported)

**ACM-2 Systems**:

- Everything (platform unknown)

---

## Enhancement Opportunities

### 🟢 Quick Wins (< 1 Week)

1. **MQTT Payload Documentation** ✅ DONE
   - Comprehensive topic reference created
   - Payload examples for all topics
   - Integration with explorer tools

2. **Enhanced Explorer Script** (Recommended)
   - Add MQTT message monitoring
   - Add response filtering/formatting
   - Add batch operation support
   - Add platform detection display

3. **Update API Documentation**
   - Add new endpoint information
   - Add platform comparison tables
   - Add MQTT integration guide

### 🟡 Medium Effort (2-4 Weeks)

1. **Add Que Platform Detection**
   - Identify Que systems in AC systems list
   - Display platform info in UI
   - Plan SignalR implementation (don't implement yet)

2. **Library Evaluation**
   - Full evaluation of `actronneoapi` v0.5.11
   - Cost-benefit analysis of migration
   - Risk assessment

3. **Multi-Account Support**
   - Query `/api/v0/client/account`
   - Track multiple systems per account
   - Improve account-level diagnostics

### 🔴 Major Features (1-3 Months)

1. **Migrate to actronneoapi Library**
   - Refactor to use external library
   - Implement multi-platform support
   - Add Neo, Que, ACM-2 simultaneously
   - Full type safety with Pydantic
   - Reduce maintenance burden

2. **Que/NX-Gen Platform Support**
   - Implement SignalR transport layer
   - Adapt coordinator for Que API
   - Que-specific entity adaptations
   - Testing against real Que systems

3. **ACM-2 Platform Support**
   - Research API structure and endpoints
   - Determine real-time transport
   - Implement client
   - Testing infrastructure

---

## Recommended Next Steps

### For Users

- ✅ All features working as intended
- ✅ MQTT real-time updates operational
- ⚠️ If you have a Que system: currently not supported (use external library)
- ⏳ ACM-2 support: on roadmap, ETA Q3/Q4 2026

### For Contributors

1. **Start Here**:
   - Read `MQTT_TOPICS_REFERENCE.md` (newly created)
   - Review `API_DISCOVERY_REPORT_2026.md` (in `.ai-scratch/`)
   - Explore explorer scripts in `/utils/`

2. **Easy Contributions**:
   - Enhance explorer script UI/features
   - Add platform detection display
   - Improve error messages

3. **Substantial Contributions**:
   - Evaluate library migration
   - Design Que platform support
   - Research ACM-2 API

### For Maintainers

1. **Immediate** (Week 1-2):
   - Publish MQTT reference documentation
   - Update explorer script README

2. **Short-term** (Month 1):
   - Evaluate `actronneoapi` migration cost/benefit
   - Plan Que platform support

3. **Medium-term** (Month 2-3):
   - Begin Que platform development
   - Contact Actron for ACM-2 API details

4. **Long-term** (Q3-Q4 2026):
   - Implement Que support
   - Start ACM-2 work
   - Potential library migration

---

## Technical Debt & Maintenance

### Current Health

- ✅ Code quality: High
- ✅ Type safety: Good (TypedDict)
- ✅ Error handling: Robust
- ✅ Test coverage: Comprehensive
- ✅ Documentation: Current
- ⚠️ Platform support: Single-platform only

### Future Improvements

- 🔄 **Type Safety**: Migrate from TypedDict to Pydantic (higher assurance)
- 🔄 **Library**: Evaluate external `actronneoapi` library for maintenance reduction
- 🔄 **Testing**: Add platform-specific test suites for Que/ACM-2
- 🔄 **Documentation**: Keep MQTT reference current as API evolves

---

## Risk Assessment

### High Risk (Avoid for Now)

- ❌ Modifying OAuth token flow (well-tested, don't touch)
- ❌ Changing MQTT topic structure (would break deployments)
- ❌ Removing polling fallback (breaks MQTT-unavailable scenarios)

### Medium Risk (Careful Refactoring)

- ⚠️ Migrating to external library (benefits outweigh risks if planned)
- ⚠️ Adding new platforms (requires separate test environment)
- ⚠️ Changing coordinator data structure (affects all entities)

### Low Risk (Good to Improve)

- ✅ Adding new endpoints (backward compatible)
- ✅ Enhancing utilities (utilities not critical path)
- ✅ Improving documentation (no code changes)
- ✅ Adding diagnostics info (purely informational)

---

## External Library Comparison

### Current: Custom Implementation

- **Pros**: Full control, minimal dependencies, proven stable
- **Cons**: Only Neo support, more maintenance, reimplemented logic

### Alternative: actronneoapi v0.5.11

- **Pros**: Multi-platform (Neo/Que/ACM-2), Pydantic types, active maintenance
- **Cons**: External dependency, potential breaking changes, larger footprint
- **Status**: Production-ready, actively maintained (latest: May 2026)
- **Fit**: 90% - Would solve platform support gap

### Migration Path (If Chosen)

```
Phase 1: Evaluation (Week 1-2)
  → Run side-by-side testing
  → Verify API compatibility
  → Check Pydantic version conflicts

Phase 2: Preparation (Week 3-4)
  → Add actronneoapi to requirements
  → Create adapter layer (minimal)
  → Prepare test environment

Phase 3: Migration (Week 5-8)
  → Swap API client implementation
  → Adapt coordinator for Pydantic models
  → Extensive testing

Phase 4: Cleanup (Week 9-10)
  → Remove duplicate code
  → Update documentation
  → Release new version

Phase 5: Multi-Platform (Week 11+)
  → Add Que support
  → Add ACM-2 support
  → Stabilize and test

Timeline: ~3 months total
```

---

## Conclusion

The ActronAir Neo integration is **feature-complete and stable for Neo platform users**. The immediate gap is **Que platform support**, which affects ~5% of potential users. The emerging opportunity is **ACM-2 support** for the new Actron Connect ecosystem.

The external `actronneoapi` library represents a viable path to close both gaps while improving type safety and reducing maintenance burden. A careful migration could position the integration for long-term multi-platform support.

**Current recommendation**: Status quo is fine for Neo users. Plan library migration for Q3 2026 to enable Que/ACM-2 support.

---

**Document Version**: 1.0 (June 7, 2026)
**Status**: Ready for Review
**Next Review**: September 2026
