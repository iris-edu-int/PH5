tag_timestamp

ascii_s
```````
:Type: String
:Range: Limited to 32 characters
:Description: Timestamp the table was created in an ascii format.  Example: Thu Dec 19 10:12:27 2019

epoch_l
```````
:Type: int 64
:Range: Limited by integer size
:Description: The timestamp in epoch seconds.  Also known as Unix time.

micro_seconds_i
```````````````
:Type: int 32
:Range: Limited by integer size
:Description: Microseconds to add to epoch

type_s
``````
:Type: String
:Range: Limited to 8 characters
:Description: Epoch, ASCII, or BOTH

end_timestamp_tag

tag_coord

value_d
'''''''
:Type: Float 64
:Range: Limited by coordinate system
:Description: Value of the coordinate

units_s
'''''''
:Type: String
:Range: Limited to 16 characters
:Description: Unit of the value

end_coord_tag

tag_corner

coordinate_system_s
```````````````````
:Type: String
:Range: Limited to 32 characters
:Description: Geographic coordinate system such as decimal degrees used for X and Y fields.

projection_s
````````````
:Type: String
:Range: Limited to 32 characters
:Description: Projection such as UTM used for X and Y fields.

ellipsoid_s
```````````
:Type: String
:Range: Limited to 32 characters
:Description: Ellipsoid used for projection such as WGS-84.

description_s
`````````````
:Type: String
:Range: Limited to 1024 characters
:Description: Description of the corner

X
`
Typically longitude in decimal degrees of the corner of a bounding box for the experiment.

.. include:: common.rst
    :start-after: tag_coord
    :end-before: end_coord_tag

Y
`
Typically latitude in decimal degrees of the corner of a bounding box for the experiment.

.. include:: common.rst
    :start-after: tag_coord
    :end-before: end_coord_tag

Z
`
Elevation typically in meters.

.. include:: common.rst
    :start-after: tag_coord
    :end-before: end_coord_tag

end_corner_tag
