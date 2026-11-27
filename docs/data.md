# Data inventory: M3DGR Outdoor01

Every fact here is tagged with where it comes from:

- **[measured]**: read from the data by the scripts below.
- **[M3DGR]**: stated in the dataset's own documentation, not checked against
  the data.
- **[inferred]**: a conclusion drawn from measurements, with the reasoning
  given.
- **[unknown]**: not established yet.

## Files

| File | Size | SHA-256 |
|---|---|---|
| `data/raw/Outdoor01.bag` | 6 553 326 739 B | `62f0d0b3f5098b5920d3c4125313daa031b176813b472b1e685b2f98c311de77` |
| `data/raw/Outdoor01.txt` | 518 307 B | `e66e7cbb2054a6c120e10299a3cf110e2a4c69bc434e865bc8bc4ba9daac42aa` |

To check that the raw files are unchanged, run `cd data && sha256sum -c SHA256SUMS`.

Source: the M3DGR dataset, <https://github.com/sjtuyinjie/M3DGR>. The
repository is MIT-licensed. Whether that license also covers the bags and
ground-truth files, which are hosted separately, is not stated. The data is
not redistributed here.

## How this was produced

```
uv run python scripts/inventory_bag.py data/raw/Outdoor01.bag outputs/inventory/bag.json
uv run python scripts/inventory_trajectory.py data/raw/Outdoor01.txt outputs/inventory/trajectory.json
MSYS_NO_PATHCONV=1 uv run python scripts/check_gt_source.py data/raw/Outdoor01.bag \
    data/raw/Outdoor01.txt /mavros/global_position/raw/fix outputs/inventory/gt_source.json
```

`MSYS_NO_PATHCONV=1` is needed in Git Bash only. Without it, Git Bash rewrites
the topic name as if it were a file path.

The record time of every message was read. `header.stamp` statistics come from
a uniform sample of about 400 messages per topic, because deserialising every
LiDAR scan in pure Python is slow. The Livox scan details come from a sample of
11 scans per LiDAR.

## Bag overview [measured]

- Format: ROS 1 bag, 16 topics.
- Record time span: 1735888008.064 to 1735888419.631 (Unix seconds), so
  411.57 s. That is 2025-01-03, 07:06 to 07:13 UTC.
- The bag contains **no `/tf`, no `/tf_static` and no `CameraInfo` topic**. All
  calibration has to come from the M3DGR documentation.

## Topics [measured]

"Record − header" is the median of the time the recorder received a message
minus the message's own `header.stamp`. A positive value means the message
arrived after the time it claims.

| Topic | Type | Count | Rate (Hz) | Max gap (s) | `frame_id` | Record − header (median) |
|---|---|---:|---:|---:|---|---:|
| `/camera/color/image_raw/compressed` | `sensor_msgs/CompressedImage` | 12 338 | 29.98 | 0.050 | `camera_color_optical_frame` | 45 ms |
| `/camera/aligned_depth_to_color/image_raw/compressedDepth` | `sensor_msgs/CompressedImage` | 12 338 | 29.98 | 0.048 | `camera_color_optical_frame` | 43 ms |
| `/camera/imu` | `sensor_msgs/Imu` | 82 321 | 200.02 | 0.015 | `camera_imu_optical_frame` | 0.4 ms |
| `/cv_camera/image_raw/compressed` (Insta360 X4) | `sensor_msgs/CompressedImage` | 6 173 | 15.00 | 0.079 | `camera` | 23 ms |
| `/livox/avia/lidar` | `livox_ros_driver/CustomMsg` | 4 115 | 10.00 | 0.109 | `livox_frame` | 108 ms |
| `/livox/avia/imu` | `sensor_msgs/Imu` | 83 695 | 203.43 | 0.108 | `livox_frame` | 60 ms |
| `/livox/mid360/lidar` | `livox_ros_driver2/CustomMsg` | 4 116 | 10.00 | 0.111 | `livox_frame` | 100 ms |
| `/livox/mid360/imu` | `sensor_msgs/Imu` | 82 312 | 199.99 | 0.019 | `livox_frame` | 0.07 ms |
| `/odom` | `nav_msgs/Odometry` | 8 231 | 20.00 | 0.061 | `odom_combined` | 0.09 ms |
| `/mavros/global_position/raw/fix` | `sensor_msgs/NavSatFix` | 6 174 | 15.00 | 0.180 | `base_link` | 4 ms |
| `/ublox_driver/receiver_lla` | `sensor_msgs/NavSatFix` | 4 116 | 10.00 | 0.112 | (empty) | −17.9 s |
| `/ublox_driver/receiver_pvt` | `gnss_comm/GnssPVTSolnMsg` | 4 116 | 10.00 | 0.112 | no header | n/a |
| `/ublox_driver/range_meas` | `gnss_comm/GnssMeasMsg` | 4 115 | 10.00 | 0.104 | no header | n/a |
| `/ublox_driver/ephem` | `gnss_comm/GnssEphemMsg` | 215 | 0.54 | 15.7 | no header | n/a |
| `/ublox_driver/glo_ephem` | `gnss_comm/GnssGloEphemMsg` | 62 | 0.16 | 30.0 | no header | n/a |
| `/ublox_driver/iono_params` | `gnss_comm/StampedFloat64Array` | 139 | 0.38 | 30.0 | (empty) | 366 s |

### Timing observations

- **Image topics arrive 25–75 ms after their `header.stamp`.** [measured] Any
  synchronisation must use `header.stamp`, not record time.
- **LiDAR scans arrive about 100 ms after `header.stamp`.** [measured] Each scan
  covers about 100 ms (see below). [inferred] The stamp marks the *start* of the
  scan, and the message is published once the scan is complete.
- **No IMU reports orientation.** [measured] On all three IMU topics the
  orientation quaternion is `0 0 0 0`, in messages 0 and 5000 of each. Only
  angular velocity and linear acceleration are usable.
- **The Avia IMU is irregular.** [measured] Its mean rate is 203 Hz against a
  nominal 200 Hz, it has gaps of up to 108 ms, and messages arrive 4–110 ms after
  their stamp. The Mid-360 IMU and the camera IMU are regular.
- **The u-blox stamps are about 18 s ahead of record time.** [measured]
  [inferred] This matches GPS time, which has been 18 s ahead of UTC since 2017.
  These topics would need that offset removed before being compared with
  anything else.
- **Four topics share `frame_id = livox_frame`:** both LiDARs and both of their
  IMUs. [measured] Frames must therefore be assigned by topic, not by
  `frame_id`.

## Discrepancies with the M3DGR documentation

| Item | M3DGR says | Bag shows |
|---|---|---|
| D435i RGB rate | 15 Hz [M3DGR] | 29.98 Hz [measured] |
| RGB topic | `/camera/color/image_raw/compressed` [M3DGR] | same, but `calibration.md` labels the intrinsics `/camera/color/image_raw` |
| RTK receiver rate | 15 Hz [M3DGR] | topic at 15 Hz, but only about 5 Hz of unique positions (see below) [measured] |
| Livox message package | `livox_ros_driver` and/or `livox_ros_driver2` [M3DGR] | Avia uses `livox_ros_driver`, Mid-360 uses `livox_ros_driver2` [measured] |

## Reference trajectory: `Outdoor01.txt`

### Format [measured]

- 6 174 rows, each with 8 whitespace-separated columns:
  `t x y z qx qy qz qw`. This is TUM layout.
- Timestamps are in Unix seconds, written to microsecond precision.
- **Every row has the identity quaternion `0 0 0 1`.** The file holds **position
  only**; orientation is not provided.
  - Consequence: ATE on position is possible.
  - Consequence: rotational RPE against this file is not.
- Only 2 861 of the rows are unique. 1 646 positions appear three times, 21
  appear twice and 1 194 appear once. Repeated rows are exact duplicates,
  timestamp included.
- The unique positions are spaced 0.199 s apart (median), so about 5 Hz.
- Timestamps are not strictly increasing: a few rows are out of order by up to
  19 µs.
- Span: 411.41 s. Horizontal extent: x from −140.0 to 1.3 m, y from −29.9 to
  25.5 m. z stays within −0.05 to 0.68 m.
- Path length over the unique positions: 345.8 m.
- Largest step between consecutive unique positions: 0.23 m.

### Source [measured, then inferred]

The file is derived from `/mavros/global_position/raw/fix`:

- The fix topic has exactly 6 174 messages, and its `header.stamp` values match
  the file's timestamps one to one, within 0.6 µs (the file's rounding).
- The vertical coordinate equals the fix altitude minus the first altitude, to
  within 0.5 µm.
- Each horizontal distance from the first fix matches the file's distance from
  its first position to within 0.15 m (RMS 0.075 m). Distances from a common
  origin are unaffected by how the axes are oriented. The fix positions were
  converted to a local east/north grid for this comparison, using a flat-earth
  approximation.
- The axes line up directly: x ≈ east and y ≈ north. The fix and file extents
  agree to within 0.16 m.

**[inferred]** `Outdoor01.txt` is the RTK GNSS fix converted to a local
east-north-up frame with its origin at the first fix. Orientation was filled
with identity, and the fix stream's duplicate messages were kept.

**[unknown]**
- The projection that was used. The 0.15 m residual is larger than the error
  of the approximation used here, so their conversion differs slightly.
- Whether the positions are RTK *fixed* or *float*. Every message reports
  `status = 0` (`STATUS_FIX`), which does not distinguish the two.
- The actual accuracy. The messages report an "approximated" covariance of
  0.49 m² horizontally (median), which is about 0.7 m standard deviation, and
  0 vertically. M3DGR states 0.8 cm horizontal accuracy for the receiver.
  These two figures disagree by two orders of magnitude, and neither has been
  checked.
- The antenna's position on the robot. M3DGR gives a GNSS → Avia offset, but
  without saying which receiver it refers to.

## Livox LiDAR messages [measured]

Both message types have the same fields. Only the package name differs.

```
Header header
uint64 timebase      # time of the first point
uint32 point_num
uint8  lidar_id
uint8[3] rsvd
CustomPoint[] points # offset_time (uint32, ns from timebase), x, y, z (float32, m),
                     # reflectivity (uint8), tag (uint8), line (uint8)
```

| | Avia | Mid-360 |
|---|---|---|
| Points per scan | 24 000 | 19 968 – 20 160 |
| Laser lines | 6 (0–5) | 4 (0–3) |
| `offset_time` range | 0 – 99.84 ms | 0 – 101.3 ms |
| `timebase` | **LiDAR's own clock**, a constant ≈ 1 735 887 530.0225 s behind `header.stamp` (±200 ns over the sample) | equal to `header.stamp` (±200 ns) |

**Consequence:** each point's time should be computed as
`header.stamp + offset_time` for both LiDARs, never from `timebase`. That is
what scan deskewing needs.

**ROS 2 conversion:** both `livox_ros_driver/CustomMsg` and
`livox_ros_driver2/CustomMsg` must be defined in the ROS 2 environment. The bag
stores their full definitions, so a converter can register both.

## Calibration [M3DGR]

Source: <https://github.com/sjtuyinjie/M3DGR/blob/main/calibration.md>. Its
convention is `p_target = R · p_source + T`, with T in metres. In this
project's notation (conventions rule 6) that is `T_target_source`.

Available:
- `camera` → `camera_imu`
- `camera` → `avia`
- `camera` → `mid360`
- `camera_imu` → `avia`
- `camera_imu` → `mid360`
- `avia` → `mid360`
- `avia` → `avia_imu` and `mid360` → `mid360_imu` (both translation only)
- GNSS antenna → `avia` (translation only)
- wheel odometry → `camera_imu`
- D435i RGB intrinsics: pinhole, 640 × 480, zero distortion
- Allan-variance noise parameters for the Avia and Mid-360 IMUs

Not available:
- Intrinsics for the Insta360 X4.
- How the D435i depth is aligned. It is published already aligned to the
  colour frame.

The values have not been copied here. They will go into `configs/`, read
directly from `calibration.md` and checked, when the first stage that needs
them is built.

[unknown] Frame names in `calibration.md` (`camera`, `avia`, …) do not match
the bag's `frame_id` values (`camera_color_optical_frame`, `livox_frame`, …).
Whether `camera` means the colour optical frame still needs to be confirmed.

## Open questions

1. GNSS accuracy and RTK fix state for Outdoor01. This determines what an ATE
   number against `Outdoor01.txt` can mean.
2. Which point on the robot the reference trajectory refers to. If it is the
   GNSS antenna, estimated trajectories must be moved to the antenna position
   before comparison.
3. The timestamp of each row is the fix time. Whether that is the measurement
   time or mavros's receive time is unknown. Record − header is about 4 ms.
4. How the D435i colour frame relates to the `camera` frame in `calibration.md`.
5. Content of the omnidirectional (Insta360 X4) images: format, and whether
   they are equirectangular or dual-fisheye.
