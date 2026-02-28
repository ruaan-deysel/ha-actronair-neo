# ActronAir HVAC Systems Catalog

Reference catalog of ActronAir systems compatible with the Neo cloud API.

> **Last updated**: February 2026. Includes data from live API testing and
> GitHub issue reports.

## Compatible Systems

| Outdoor Unit | Indoor Unit | Series            | Phase | Capacity |
| ------------ | ----------- | ----------------- | ----- | -------- |
| CRA100S      | EVA100S     | Classic           | 1     | 10.16 kW |
| CRA130S      | EVA130S     | Classic           | 1     | 12.24 kW |
| CRA150S      | EVA150S     | Classic           | 1     | 14.97 kW |
| CRA170S      | EVA170S     | Classic           | 1     | 16.80 kW |
| CRA130T      | EVA130S     | Classic           | 3     | 12.40 kW |
| CRA150T      | EVA150S     | Classic           | 3     | 14.68 kW |
| CRA170T      | EVA170S     | Classic           | 3     | 16.99 kW |
| CRA200T      | EVA200S     | Classic           | 3     | 19.06 kW |
| CRA230T      | EVA230S     | Classic           | 3     | 22.35 kW |
| CRV13AS      | EVV13AS-V   | Advance           | 1     | 13.0 kW  |
| CRV15AS      | EVV15AS-V   | Advance           | 1     | 15.0 kW  |
| CRV17AS      | EVV17AS-V   | Advance           | 1     | 17.0 kW  |
| CRV15AT      | EVV15AS     | Advance           | 3     | 15.0 kW  |
| CRV17AT      | EVV17AS     | Advance           | 3     | 17.0 kW  |
| CRV210T      | EVV210S     | Advance           | 3     | 21.0 kW  |
| CRV240T      | EVV240S     | Advance           | 3     | 24.0 kW  |
| CRV15BS      | EVV15BS     | Advance S2        | 3     | 15.0 kW  |
| CRS17AT      | EVA17AS     | Aires             | 1     | 17.0 kW  |
| CRS20AT      | EVA20AS     | Aires             | 3     | 20.0 kW  |
| CRQ24AT      | —           | Que (Neo upgrade) | 3     | 24.0 kW  |

## Controllers

| Model               | Description                       | Interface         |
| ------------------- | --------------------------------- | ----------------- |
| NTW-1000            | Neo Touch Wall Controller (White) | Touchscreen + BLE |
| NTB-1000            | Neo Touch Wall Controller (Black) | Touchscreen + BLE |
| NTB-10 / NTW-10     | Neo Touch (compact variant)       | Touchscreen       |
| NZB-100             | Neo Zone Controller (Black)       | Zone sensor       |
| NZW-100             | Neo Zone Controller (White)       | Zone sensor       |
| QTB-1000 / QTW-1000 | Que Touch Wall Controller         | Touchscreen       |
| LR7-1W/G            | 7-day wall controller (8-zone)    | Button/display    |
| LM7-1W/G            | 7-day programmable controller     | Button/display    |
| LM24W               | 8-zone integrated controller      | Button/display    |
| LC75                | Legacy controller                 | —                 |

## Sensors

| Model             | Description                         | Type         |
| ----------------- | ----------------------------------- | ------------ |
| NSB-10 / NSW-10   | Neo Sense Zone Sensor (Black/White) | Wireless BLE |
| QSB-10 / QSW-10   | Que Remote Sensor (Black/White)     | Wireless     |
| LM-ZS-2W          | M-Series Zone Sensor                | Wired        |
| LM-RS-2W          | M-Series Remote Wall Sensor         | Wired        |
| LM-RAS            | "Averaging" Room Wall Sensor        | Wired        |
| AERSS             | Return Air Duct Sensor              | Duct mount   |
| NSHB-10 / NSHW-10 | Neo Sensor Holder (Black/White)     | Accessory    |

## Series Details

### Classic Series

- **Compressor**: Fixed speed
- **Operating range**: -10°C to 50°C
- **Outdoor unit family** (API): `"Fixed Speed: Classic"`
- **Features**: EC inverter indoor fan, up to 8 zones
- **Limitations**:
  - No AUTO fan mode (`NV_AutoFanEnabled: false`)
  - No Turbo mode (`TurboMode.Supported: false`)
  - No Variable Fan Technology (`VFT.Supported: false`)
  - No outdoor temperature sensor (`LiveOutdoorTemp_oC: 3000.0`)
  - No Dry mode (`ModeSupport.Dry: false`)
- **Verified models**: EVA150S indoor + NTW-1000 controller (GitHub issue data
  and live API test)

### Advance Series (including Series 2)

- **Compressor**: Tru-Inverter Variable Speed Scroll
- **Operating range**: -15°C to 54°C
- **Features**:
  - Individual Temperature Control (ITC)
  - Variable Fan Technology (VFT)
  - AUTO fan mode
  - Turbo mode
  - Quiet mode with sound reduction
  - Vertical discharge option
  - Energy Smart Zoning
  - Blue fin epoxy coated coils
  - BMS option
  - R410A refrigerant
- **Series 2 additions**: CRV15BS/EVV15BS outdoor/indoor pair confirmed in
  GitHub issue #33

### Aires Series

- **Compressor**: Inverter Twin Rotary
- **Operating range**: -10°C to 50°C
- **Features**:
  - Compact outdoor unit design
  - Unity IQ Logic
  - Quiet mode
  - Flexible zoning
  - Automatic capacity adjustment

### Que-to-Neo Upgrades

Some Que systems have been upgraded to Neo controllers by Actron. These units:

- Use the Neo app and Neo cloud API (`nimbus.actronair.com.au`)
- May have Que outdoor/indoor units with Neo wall controllers
- Can experience 503 errors on commands (GitHub issue #59: CRQ24AT)
- The `actronneoapi` library supports both Neo and Que platforms with auto-detection

## Known Issues by Model

| Model / Series       | Issue                                        | GitHub |
| -------------------- | -------------------------------------------- | ------ |
| NTB-10               | AUTO fan not available (bitmap=4, HIGH only) | #10    |
| Advance S2 (CRV15BS) | Zone climate shows ON when system OFF        | #33    |
| Classic              | Ambient temp "Unknown" (3000.0 sensor error) | #57    |
| CRQ24AT (Que→Neo)    | 503 errors, entities duplicated              | #59    |
| All                  | Events API disabled by Actron (July 2025)    | —      |

## API Identification Fields

These fields in the status API response identify the hardware:

```text
AirconSystem.MasterWCModel          → Wall controller model (e.g., "NTW-1000")
AirconSystem.IndoorUnit.NV_ModelNumber → Indoor unit (e.g., "EVA150S")
AirconSystem.OutdoorUnit.Family     → Series (e.g., "Fixed Speed: Classic")
AirconSystem.OutdoorUnit.CtrlBoardType → Board type (e.g., "Type 100: UnoJr")
AirconSystem.OutdoorUnit.Capacity_kW → Rated capacity
AirconSystem.IndoorUnit.NV_SupportedFanModes → Bitmask (1=LOW,2=MED,4=HIGH,8=AUTO)
AirconSystem.IndoorUnit.NV_AutoFanEnabled → AUTO fan available
UserAirconSettings.ModeSupport      → Supported HVAC modes
UserAirconSettings.TurboMode.Supported → Turbo available
UserAirconSettings.VFT.Supported    → VFT available
```

## Changelog

- **February 2026**: Added Advance Series 2 (CRV15BS/EVV15BS), Que-to-Neo
  upgrades (CRQ24AT), NTB-10 controller. Added known issues table from GitHub
  issue history. Added API identification fields reference. Documented
  model-specific feature availability from live API testing.
