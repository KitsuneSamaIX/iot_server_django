A Django based server integrated with AWS IoT core services to handle fleets of IoT devices.

The server handles all aspects of the life cycle of an IoT device including:

- Auto fleet provisionig and first registration to the server's DB.
- Reception and storage of log data sended from devices.
- Aggregate analysis and creation of plots over stored data.
- Handling of Job queues on IoT devices.
- Rest API to expose backend services to frontend applications.
