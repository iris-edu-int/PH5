##################
PH5 Archive Format
##################
This document is intended to provide detailed information on specific fields which
are contained within PH5 files.  For information on how to create PH5 files
see https://github.com/PIC-IRIS/PH5/wiki/PH5-Creating-Validating-and-Archiving.
For general information see https://github.com/PIC-IRIS/PH5/wiki.

************
Experiment_g
************
The Experiment Group is the primary group.  Within the Experiment Group the
data and metadata are further organized into four main groups: Receivers,
Reports, Responses and Sorts.  In addition to these groups, the experiment
table exists to hold survey metadata.

.. include:: experiment_t.rst

Maps_g
======
An additional index used by segd and segy files

.. TODO maybe reference Receivers_g/Das_g_XXXXX/index_t instead of having
    them separate.

index_t
-------
This table relates mini files, hdf5 paths, and time sliced DAS data.  Note
much of the information stored in this table is duplicated in
Receivers_g/Das_g_XXXXX/index_t.

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

.. include:: receivers_g.rst

.. include:: sorts_g.rst


Responses_g
===========
The response group contains response information for the sensor data logger combinations.

xxxxx
-----
The response array is a textural array holding response information in RESP
format.  The name is based on input from resp_load.

Response_t
----------
Contains information about instrument response including both data logger and sensor.

The response table holds, bit weight, gain, and a reference to the RESP files.

response_file_a
```````````````
:Type: String
:Range: Limited to 32 characters
:Description: Response file name

response_file_das_a
```````````````````
:Type: String
:Range: Limited to 128 characters
:Description: Response text array name to reference for DAS data conversion.

response_file_sensor_a
``````````````````````
:Type: String
:Range: Limited to 128 characters
:Description: Response text array name to reference for sensor data conversion.

n_i
```
:Type: int 32
:Range: Limited by integer size
:Description: This stores an index number (foreign key) which is referenced by
    both das_t and array_xxx_t as response_table_n_i.

bit_weight
``````````
Conversion value from bit to unit such as voltage

value_d
'''''''
:Type: Float 64
:Description: Scalar to multiply by bit value

units_s
'''''''
:Type: String
:Range: Limited to 16 characters
:Description: The unit of scalar typically volts per count

gain
````
Gain of response

value_d
'''''''
:Type: int 32
:Range: Limited by integer size
:Description: Gain of response

units_s
'''''''
:Type: String
:Range: Limited to 16 characters
:Description: The unit of gain typically dB

Reports_g
=========
This group holds any reports related to survey.

Report_a_xxxx
-------------
Contains binary report information typical files are pdfs of microsoft word documents.

Report_t
--------
Metadata for a given report stored in PH5.

array_name_a
````````````
:Type: String
:Range: Limited to 32 characters
:Description: Name of array where file is stored.

description_s
`````````````
:Type: String
:Range: Limited to 1024 characters
:Description: Description of report stored in PH5.

format_s
````````
:Type: String
:Range: Limited to 32 characters
:Description: Report file type of format e.g. pdf, odt, doc, ...

title_s
```````
:Type: String
:Range: Limited to 64 characters
:Description: Title of report stored in PH5.

*******************
Field Relationships
*******************

.. image:: field-relations.svg
    :target: _images/field-relations.svg

.. include:: field_relations.rst
