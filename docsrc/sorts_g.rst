Sorts_g
=======
This group contains a logical grouping of receivers and shots a.k.a arrays.
These group referenced back via geometry and time to allow efficent experiment
level access.

Array_t_xxx
-----------
The array table(s) contain receiver geometry and metadata such as deploy /
pickup times and DAS physical information.

id_s
````
:Type: String
:Range: Limited to 16 characters
:Description: Shot ID

channel_number_i
````````````````
:Type: int 8
:Range: Limited by integer size
:Description: Channel number of a given data stream from DAS

description_s
`````````````
:Type: String
:Range: Limited to 16 characters
:Description: Description of time-series data

seed_band_code_s
````````````````
:Type: String
:Range: Limited to 1 character
:Description: This one letter field specifies the general sampling rate and the
    response band of the instrument.
    See https://ds.iris.edu/ds/nodes/dmc/data/formats/seed-channel-naming/ for
    more details.

seed_instrument_code_s
``````````````````````
:Type: String
:Range: Limited to 1 character
:Description: This one letter field specifies the family to which the sensor
    belongs. In essence, this identifies what is being measured. Each of
    these instrument types are detailed in this section.
    See https://ds.iris.edu/ds/nodes/dmc/data/formats/seed-channel-naming/ for
    more details.

seed_orientation_code_s
```````````````````````
:Type: String
:Range: Limited to 1 character
:Description: This one letter field is the Orientation Code, which provides
    a way to indicate the directionality of the sensor measurement.
    See https://ds.iris.edu/ds/nodes/dmc/data/formats/seed-channel-naming/ for
    more details.

seed_location_code_s
````````````````````
:Type: String
:Range: Limited to 2 characters
:Description: This code allows to better uniquely identify a seismogram.
    See https://ds.iris.edu/ds/newsletter/vol1/no1/1/specification-of-seismograms-the-location-identifier/
    for more details.

seed_station_name_s
```````````````````
:Type: String
:Range: Limited to 5 characters
:Description: A 1 to 5 character identifier for the station recording the data
    Also known as station code.

sample_rate_i
`````````````
:Type: int 16
:Range: Limited by integer size
:Description: Sampling rate (samples/second) of data stored.

sample_rate_multiplier
``````````````````````
:Type: int 16
:Range: Limited by integer size
:Description: Sample rate multiplier needed for when sample are less than 1 SPS.

receiver_table_n_i
``````````````````
:Type: int 32
:Range: Limited by integer size
:Description: Receiver table (Receivers_g/Receivers_t) index (zero based).

response_table_n_i
``````````````````
:Type: int 32
:Range: Limited by integer size
:Description: Response table (Responses_g/Responses_t) index (zero based).

location
````````
location of sensor

coordinate_system_s
''''''''''''''''''''
:Type: String
:Range: Limited to 32 characters
:Description: Geographic coordinate system such as decimal degrees used for X and Y fields.

projection_s
'''''''''''''
:Type: String
:Range: Limited to 32 characters
:Description: Projection such as UTM used for X and Y fields.

ellipsoid_s
'''''''''''
:Type: String
:Range: Limited to 32 characters
:Description: Ellipsoid used for projection such as WGS-84.

description_s
'''''''''''''
:Type: String
:Range: Limited to 1024 characters
:Description: Description of array location.

X
.
Typically latitude or northing

.. include:: common.rst
    :start-after: tag_coord
    :end-before: end_coord_tag
Y
.
Typically longitude or easting

.. include:: common.rst
    :start-after: tag_coord
    :end-before: end_coord_tag
Z
.
Elevation

.. include:: common.rst
    :start-after: tag_coord
    :end-before: end_coord_tag

deploy_time
```````````
Time when an array was deployed.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

pickup_time
```````````
Time when an array was picked up.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

das
```
Information about digital acquisition system used to collect data.

serial_number_s
''''''''''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Serial number of DAS.

model_s
''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Model name of DAS given by the manufacturer.

manufacturer_s
''''''''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Manufacturer of DAS.

notes_s
''''''''
:Type: String
:Range: Limited to 1024 characters
:Description: Additional notes on DAS

sensor
``````
Sensor attached to given channel such as geophone and seismometer.

serial_number_s
'''''''''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Serial number of sensor

model_s
'''''''
:Type: String
:Range: Limited to 64 characters
:Description: Model of sensor.

manufacturer_s
''''''''''''''
:Type: String
:Range: Limited to 64 characters
:Description: Manufacturer of sensor

notes_s
'''''''
:Type: String
:Range: Limited to 1024 characters
:Description: Notes on sensor

Sort_t
------
This table provides summary of array tables versus start and end times.

array_name_s
````````````
:Type: String
:Range: Limited to 16 characters
:Description: Array name

array_t_name_s
``````````````
:Type: String
:Range: Limited to 16 characters
:Description: Array table name within Sorts_g group.

description_s
`````````````
:Type: String
:Range: Limited to 1024 characters
:Description: Description of array entry.  By default a recording window
    reference is listed.

event_id_s
``````````
:Type: String
:Range: Limited to 16 characters
:Description: Event ID if array is associated with an event such as shot.

start_time
``````````
Start time of data segment.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

end_time
````````
End time of data segment.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

time_stamp
``````````
Time table entry was created.

.. include:: common.rst
    :start-after: tag_timestamp
    :end-before: end_timestamp_tag

Offset_t_xxx
------------
This table is derived from shot location versus receiver location.

receiver_id_s
`````````````
:Type: String
:Range: Limited to 16 characters
:Description: The ID of a receiver found in Array_t_XXX

offset
``````
Distance offset from receiver to event.

value_d
'''''''
:Type: Float 64
:Description: Value of offset distance

units_s
'''''''
:Type: String
:Range: Limited to 16 characters
:Description: The unit of offset.  Typically in meters.

event_id_s
```````````
:Type: String
:Range: Limited to 16 characters
:Description: The ID found in Event_t_XXX

azimuth
```````
Angle offset from receiver to event.

value_f
'''''''
:Type: Float 32
:Description: Value of offset azimuth angle

units_s
'''''''
:Type: String
:Range: Limited to 16 characters
:Description: The unit of azimuth angle typically degrees.
