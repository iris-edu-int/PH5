Experiment group:
=================
This HDF5 group is the top level group for the file.  All other groups
mentioned in subsequent sections are under this group.  There also exists an
experiment table which contains general information on the experiment such as
enumerating PIs and institutions involved.  The experiment table does not
contain any direct references however it holds the northwest and southeast
corners to define a rough geographic boundary of experiment data.

Receivers group:
================
This group holds the binary information from DAS units.  Within this group
there are typically many individual DAS_g_XXXX (XXXX is serial number).  Within
each DAS group data is further distributed into individual Data_a_XXXX arrays
hold the time series or “waveform” data for a particular DAS can be found
in DAS_g_XXXX.Das_t.  The Das_t table has the following references to other tables:

 * DAS_g_XXXX.Das_t.array_name_data_a to a particular Data_a_XXXX
 * DAS_g_XXXX.Das_t.receiver_table_n_i to Receivers_g.Receiver_t.(implied_index)
 * DAS_g_XXXX.Das_t.response_table_n_i to Response_g.Response_t.n_i

Additionally within the receivers group, three tables exist for additional data
attributes.  First, DAS_g_XXXX.index_t references exactly which mini file each
DASes information and provides start and end times of data if temporal sorting
is desired.  Second, receiver_t holds orientation information that is
referenced by Sorts_g.Array_t.receiver_table_n_i and
DAS_g_XXXX.Das_t.receiver_table_n_i.  Thirdly, for DASes which do not auto
correct clock time_t provides slope and offset for this purpose.

Maps group:
===========
Additional tables are created when ingesting segd or segy files.  These tables
are similar to Receiver group’s DAS_g_XXXX.index_t and references exactly which
mini file each DASes information and provides start and end times of data if
temporal sorting is desired.  These DAS_g_XXXX.index_t are listed in
Maps_g.index_t so that each individual DAS can be referenced.

Reports group:
==============
This group holds any reports related to the experiment.  There are no direct or
explicit relations between this group and any other within the archive.

Responses group:
================
The response group contains response information for the sensor data logger
combinations.  These responses are referenced by both sorts and receivers
groups and these specific references are documented in those specific sections.

Sorts group:
============
This group is responsible for relating and providing references to arrays,
events, and responses stored in all the other groups and tables.

**Event_t** lists the shot events time, location, and potentially magnitude the
id_s is later referenced in Event_t_XXX tables.

**Offset_t_XXX_XXX** (Offset_t_array#_event#) are tables which describe angle
and physical distance between array and events.

**Sort_t** table summarizes arrays versus times which allows one to further
reference Array_t_XXX tables for more specifics.

Array_t_XXX:
------------
Is a logical grouping location, deploy times, and DAS / Sensor information.
Each id represents a station. Each row is a different channel of a given
sensor.  There are two key references to other tables:

 * Array_t.response_table_n_i points to Response_g.Response_t.n_i
 * Array_t.receiver_table_n_i points to Receivers_g.Receiver_t.(implied_index)



