Receivers_g
===========
The receivers group holds trace data, metadata related to trace data, and links to the miniPH5_#####.ph5 files
containing timeseries data.

Das_g_xxxxx
-----------
Holds data from a given data logger or station.  "xxxxxx" is based off serial number of
data aquisition system (DAS).

Data_a_xxxx
```````````
The data array holds binary time series or textural data, usually in 32 bit
floats or 32 bit integers.  This data originated from DAS raw files.

Das_t
`````
The das table holds information about the data from a given data logger.  This table
links Data_a_xxxx to which raw file it came from and in the case of a multiple channel
DAS which channel a given.

array_name_SOH_a
''''''''''''''''
:Type: String
:Range: Limited to 16 characters
:Description: State of health from logger if applicable to given instrument

array_name_data_a
'''''''''''''''''
:Type: String
:Range: Limited to 16 characters
:Description: Reference to array where raw data is stored.

array_name_event_a
''''''''''''''''''
:Type: String
:Range: Limited to 16 characters
:Description: Used by RT125s for datalogger events not shot or earthquake events. This is populated from the
    “event table” that is programmed into the rt125 that describe how and when to record.

array_name_log_a
''''''''''''''''
:Type: String
:Range: Limited to 16 characters
:Description: These are ASCII logs from the dataloggeer that record operational
    information.

channel_number_i
''''''''''''''''
:Type: int 8
:Range: Limited by integer size
:Description: Channel number from DAS typically each channel is an axis of a
    geophone or seismometer.

event_number_i
''''''''''''''
:Type: int 32
:Range: Limited by integer size
:Description: This correlates event number to where data is stored in PH5.

raw_file_name_s
'''''''''''''''
:Type: String
:Range: Limited to 32 characters
:Description: Name of the raw file from data logger i.e. \*.TRD which has been
    ingested by PH5.

receiver_table_n_i
''''''''''''''''''
:Type: int 32
:Range: Limited by integer size
:Description: Index to receiver table located in Receivers group.  This table
    provides orientation information.

response_table_n_i
''''''''''''''''''
:Type: int 32
:Range: Limited by integer size
:Description: Index to response table located at Response_g/Response_t.  This table
    and group provides model to change from raw bits to meaningful measurements like
    volts.

sample_count_i
''''''''''''''
:Type: int 32
:Range: Limited by integer size
:Description: Number of samples in array referenced.

sample_rate_i
'''''''''''''
:Type: int 16
:Range: Limited by integer size
:Description: Sampling rate (samples/second) of data stored in array.

sample_rate_multiplier_i
''''''''''''''''''''''''
:Type: int 16
:Range: Limited by integer size
:Description: Sample rate multiplier needed for when sample are less than 1 SPS.

stream_number_i
'''''''''''''''
:Type: int 8
:Range: Limited by integer size
:Description: Stream number from DAS

time
''''
Time from DAS trace.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

Event_a_xxxx
````````````
The event array holds textural data about event windows programmed in the data logger.

SOH_a_xxxx
``````````
The SOH array holds textural data about the data logger state of health.

Log_a_xxxx
``````````
The log array holds textural log information.

Index_t
-------
This table relates mini files, hdf5 paths, and time sliced DAS data.

external_filename_s
```````````````````
:Type: String
:Range: Limited to 32 characters
:Description: Name of mini PH5 file used to store DAS data.

hdf5_path_s
```````````
:Type: String
:Range: Limited to 64 characters
:Description: HDF5 path which is typically used to reference DAS data

serial_number_s
```````````````
:Type: String
:Range: Limited to 64 characters
:Description: DAS serial number which data originated from.

start_time
``````````
Start time of reference.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag


end_time
````````
End time of reference.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

time_stamp
``````````
The time the index entry was created.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

Receiver_t
----------
Orientation
```````````
Channel orientation of sensor.  This information is referenced via Das_t

description_s
'''''''''''''
:Type: String
:Range: Limited to 1024 characters
:Description: Description of orientation.  Typically a short hand such as
    N, E, or Z.

channel_number_i
''''''''''''''''
:Type: int 8
:Range: Limited by integer size
:Description: Channel number within DAS however since rest of file is
    broken up by channel typically 0.

azimuth
'''''''
Azimuth angle of sensor channel.

value_f
.......
:Type: Float 32
:Range: Limited by coordinate system
:Description: Orientation angle of sensor channel.

units_s
.......
:Type: String
:Range: Limited to 16 characters
:Description: Unit of azimuth value typically radians or degrees.

dip
'''
dip of station

value_f
.......
:Type: Float 32
:Range: Limited by coordinate system
:Description: Dip angle of sensor channel.

units_s
.......
:Type: String
:Range: Limited to 16 characters
:Description: Unit of dip value typically radians or degrees.

Time_t
------
Time table to correct for free oscillators.  Currently used by Texans.

corrected_i
```````````
:Type: int 16
:Range: Limited by integer size
:Description: Boolean if time was corrected.

description_s
`````````````
:Type: String
:Range: Limited to 1024 characters
:Description: Includes station and channel from SEED file.

offset_d
````````
:Type: Float 64
:Range: Limited by Float 64 precision
:Description: SEED time correction offset in units of 0.0001 per.

slope_d
```````
:Type: Float 64
:Range: Limited by Float 64 precision
:Description: SEED time correction slope.

das
```
notes_s
'''''''
:Type: String
:Range: Limited to 1024 characters
:Description: Notes field for DAS, not commonly used.

model_s
'''''''
:Type: String
:Range: Limited to 64 characters
:Description: Model of DAS, not commonly used.

serial_number_s
'''''''''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Serial number of DAS.

manufacturer_s
''''''''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Manufacturer of DAS.

start_time
``````````
Start time of correction.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

end_time
````````
End time of correction.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag
