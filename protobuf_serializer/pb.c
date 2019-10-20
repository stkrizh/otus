#include <Python.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>
#include "deviceapps.pb-c.h"


#define MAGIC  0xFFFFFFFF
#define DEVICE_APPS_TYPE 1
#define PBHEADER_INIT {MAGIC, 0, 0}

#define STATUS_OK 0
#define STATUS_ERROR_SERIALIZATION -1
#define STATUS_ERROR_MEMORY -2


typedef struct pbheader_s {
    uint32_t magic;
    uint16_t type;
    uint16_t length;
} pbheader_t;


/* ======================================================================
    Pack value of `device` field from `py_message` (supposed to be an instance
    of Python's `dict` type) to protobuf message `msg`.
    
    `device` must be a dict.

    For example:
    py_message = {"device": {id": "123456", "type": "foo"}, ...}
*/
int pack_device(DeviceApps* msg, PyObject* py_message) {

    PyObject* py_device;
    PyObject* py_device_id;
    PyObject* py_device_type;
    const char* device_id;
    const char* device_type;

    py_device = PyDict_GetItemString(py_message, "device");

    if (py_device) {
        if (!PyDict_Check(py_device))
            return STATUS_ERROR_SERIALIZATION;

        py_device_id = PyDict_GetItemString(py_device, "id");
        device_id = py_device_id ? PyUnicode_AsUTF8(py_device_id) : NULL;

        if (device_id != NULL) {
            msg->device->has_id = 1;
            msg->device->id.data = (uint8_t*) device_id;
            msg->device->id.len = strlen(device_id);
        }

        py_device_type = PyDict_GetItemString(py_device, "type");
        device_type = py_device_type ? PyUnicode_AsUTF8(py_device_type) : NULL;

        if (device_type != NULL) { 
            msg->device->has_type = 1;
            msg->device->type.data = (uint8_t*) device_type;
            msg->device->type.len = strlen(device_type);
        }
    }

    if (PyErr_Occurred() != NULL)
        return STATUS_ERROR_SERIALIZATION;

    return STATUS_OK;
}


/* ======================================================================
    Pack value of ``lat` field from `py_message` (supposed to be an instance
    of Python's `dict` type) to protobuf message `msg`.

    `lat` must be a number.

    For example:
    py_message = {"lat": 53.45678, ...}
*/
int pack_lat(DeviceApps* msg, PyObject* py_message) {

    PyObject* py_lat;
    double c_lat;
    
    py_lat = PyDict_GetItemString(py_message, "lat");

    if (py_lat) {
        c_lat = PyFloat_AsDouble(py_lat);

        if (PyErr_Occurred() != NULL) {
            return STATUS_ERROR_SERIALIZATION;
        } 

        msg->has_lat = 1;
        msg->lat = c_lat;
    }

    return STATUS_OK;
}


/* ======================================================================
    Pack value of `lon` field from `py_message` (supposed to be an instance 
    of Python's `dict` type) to protobuf message `msg`.

    `lon` must be a number.

    For example:
    py_message = {"lon": 53.45678, ...}
*/
int pack_lon(DeviceApps* msg, PyObject* py_message) {

    PyObject* py_lon;
    double c_lon;
    
    py_lon = PyDict_GetItemString(py_message, "lon");

    if (py_lon) {
        c_lon = PyFloat_AsDouble(py_lon);

        if (PyErr_Occurred() != NULL) {
            return STATUS_ERROR_SERIALIZATION;
        }

        msg->has_lon = 1;
        msg->lon = c_lon;
    }

    return STATUS_OK;
}


/* ======================================================================
    Pack value of `apps` field from `py_message` (supposed to be an instance 
    of Python's `dict` type) to protobuf message `msg`.

    `apps` must be a list of integers.

    For example:
    py_message = {"apps": [1, 2, 3], ...}
*/
int pack_apps(DeviceApps* msg, PyObject* py_message) {

    PyObject* apps;
    PyObject* apps_item;
    int overflow;
    size_t origin_apps_len;
    size_t i;
    size_t len = 0;
    long item;

    apps = PyDict_GetItemString(py_message, "apps");

    if (apps) {

        if (!PyList_Check(apps))
            return STATUS_ERROR_SERIALIZATION;

        origin_apps_len = PyList_Size(apps);
        
        if (origin_apps_len) {
            
            msg->apps = malloc(sizeof(uint32_t) * origin_apps_len);
            if (!msg->apps)
                return STATUS_ERROR_MEMORY;

            for (i = 0; i < origin_apps_len; i++) {
                apps_item = PyList_GetItem(apps, i);
                if (!PyLong_Check(apps_item))
                    continue;

                item = PyLong_AsLongAndOverflow(apps_item, &overflow);

                if (overflow || item < 0 || item > UINT32_MAX)
                    continue;

                msg->apps[len] = item;
                len++;
            }
        }
    }

    msg->n_apps = len;
    return STATUS_OK;
}


/* ======================================================================
   Serialize `py_message` (supposed to be an instance of `dict` class) 
   with protobuf and write it to `file`. The message is preceded by
   a special header (see `pheader_t` structure).
*/
int write_message(gzFile file, PyObject* py_message) {

    DeviceApps msg = DEVICE_APPS__INIT;
    DeviceApps__Device device = DEVICE_APPS__DEVICE__INIT;
    int bytes_written_body;
    int bytes_written_header;
    int status;
    pbheader_t message_header = PBHEADER_INIT;
    size_t packed_size;
    void* message_body;

    msg.device = &device;

    status = pack_device(&msg, py_message);
    if (status != STATUS_OK)
        return status;

    status = pack_lat(&msg, py_message);
    if (status != STATUS_OK)
        return status;

    status = pack_lon(&msg, py_message);
    if (status != STATUS_OK)
        return status;

    status = pack_apps(&msg, py_message);
    if (status != STATUS_OK)
        return status;

    packed_size = device_apps__get_packed_size(&msg);
    message_body = malloc(packed_size);
    if (!message_body)
        return STATUS_ERROR_MEMORY;

    // Pack message to `message_body` buffer
    device_apps__pack(&msg, message_body);
    free(msg.apps);

    // Write header
    message_header.type = DEVICE_APPS_TYPE;
    message_header.length = packed_size;
    bytes_written_header = gzwrite(file, &message_header , sizeof(message_header));

    // Write message
    bytes_written_body = gzwrite(file, message_body, packed_size);
    free(message_body);

    if (
        (bytes_written_header != sizeof(message_header)) ||
        (bytes_written_body != (int) packed_size)
    )
        return STATUS_ERROR_SERIALIZATION;

    return bytes_written_header + bytes_written_body;
}


/* ======================================================================
   Read iterator of Python dicts.
   Pack them to DeviceApps protobuf and write to file with appropriate header.
   Return number of written bytes as Python integer.
*/
static PyObject* py_deviceapps_xwrite_pb(PyObject* self, PyObject* args) {
    
    gzFile file;
    PyObject* iterable;
    PyObject* iterator;
    PyObject* py_message;
    const char* path;
    int total_bytes_written = 0;
    int written = 0;

    if (!PyArg_ParseTuple(args, "Os", &iterable, &path))
        return NULL;

    iterator = PyObject_GetIter(iterable);
    if (iterator == NULL) {
        PyErr_SetString(PyExc_TypeError, "First argument must be an iterable.");
        return NULL;
    }

    file = gzopen(path, "wb");
    if (file == NULL) {
        PyErr_SetString(PyExc_OSError, "Could not open the file.");
        Py_DECREF(iterator);
        return NULL;
    }

    while ((py_message = PyIter_Next(iterator))) {

        if (!PyDict_Check(py_message)) {
            Py_DECREF(py_message);
            continue;
        }
 
        written = write_message(file, py_message);
        Py_DECREF(py_message);

        if (written == STATUS_ERROR_MEMORY) {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate enough memory.");
            Py_DECREF(iterator);
            gzclose(file);
            return NULL;
        }

        if (written == STATUS_ERROR_SERIALIZATION) {
            PyErr_SetString(PyExc_Exception, "Could not serialize the data.");
            Py_DECREF(iterator);
            gzclose(file);
            return NULL;
        }

        total_bytes_written += written;
    }

    Py_DECREF(iterator);
    gzclose(file);

    return PyLong_FromLong(total_bytes_written);
}


/* ======================================================================
    Unpack `device` field of protobuf `message` and convert it to 
    `PyObject` that represents a dictionary with `id` and `type` keys.

    Returns `NULL` if an error occured.
*/
PyObject* unpack_device(DeviceApps* message) {

    PyObject* device;
    PyObject* value;
    int is_error;

    device = PyDict_New();

    if (device == NULL) {
        PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
        return NULL;
    }

    // Return an empty dict if there is no `device`
    if (message->device == NULL)
        return device;

    if (message->device->has_id) {
        value = PyUnicode_DecodeUTF8(
            (char*) message->device->id.data, message->device->id.len, "strict"
        );

        if (value == NULL) {
            PyErr_SetString(PyExc_UnicodeDecodeError, "Unicode error.");
            Py_DECREF(device);
            return NULL;
        }

        is_error = PyDict_SetItemString(device, "id", value);
        Py_DECREF(value);

        if (is_error) {
            PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
            Py_DECREF(device);
            return NULL;
        }
    }

    if (message->device->has_type) {
        value = PyUnicode_DecodeUTF8(
            (char*) message->device->type.data, message->device->type.len, "strict"
        );

        if (value == NULL) {
            PyErr_SetString(PyExc_UnicodeDecodeError, "Unicode error.");
            Py_DECREF(device);
            return NULL;
        }

        is_error = PyDict_SetItemString(device, "type", value);
        Py_DECREF(value);

        if (is_error) {
            PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
            Py_DECREF(device);
            return NULL;
        }
    }

    return device;
}


/* ======================================================================
    Unpack `lat` field of protobuf `message` and convert it to 
    `PyObject` that represents a float number.

    Returns `NULL` if `lat` is not set.
*/
PyObject* unpack_lat(DeviceApps* message) {

    if (!message->has_lat)
        return NULL;

    return PyFloat_FromDouble(message->lat);
}


/* ======================================================================
    Unpack `lon` field of protobuf `message` and convert it to 
    `PyObject` that represents a float number.

    Returns `NULL` if `lon` is not set.
*/
PyObject* unpack_lon(DeviceApps* message) {

    if (!message->has_lon)
        return NULL;

    return PyFloat_FromDouble(message->lon);
}


/* ======================================================================
    Unpack `apps` field of protobuf `message` and convert it to 
    `PyObject` that represents a list of integers.

    Returns `NULL` if an error occured.
*/
PyObject* unpack_apps(DeviceApps* message) {

    PyObject* apps;
    PyObject* item;
    int is_error;
    size_t i;

    apps = PyList_New(message->n_apps);
    if (apps == NULL) {
        PyErr_SetString(PyExc_Exception, "Could not create a list instance.");
        return NULL;
    }

    for (i = 0; i < message->n_apps; i++) {
        item = PyLong_FromUnsignedLong(message->apps[i]);

        if (item == NULL) {
            PyErr_SetString(PyExc_Exception, "Could not create a list instance.");
            Py_DECREF(apps);
            return NULL;
        }

        // `PyList_SetItem` "steals" ownership of `item` reference
        // https://docs.python.org/3/c-api/list.html#c.PyList_SetItem
        is_error = PyList_SetItem(apps, i, item);

        if (is_error) {
            PyErr_SetString(PyExc_Exception, "Could not create a list instance.");
            Py_DECREF(apps);
            return NULL;
        }
    }

    return apps;
}


/* ======================================================================
    Unpack protobuf `message` and convert it to `PyObject` that 
    represents a dictionary with `device`, `lat`, `lon`, `apps` keys.

    Returns `NULL` if an error occured.
*/
PyObject* unpack_message(DeviceApps* message) {

    PyObject* py_message;
    PyObject* device;
    PyObject* lat;
    PyObject* lon;
    PyObject* apps;
    int is_error;

    py_message = PyDict_New();

    if (py_message == NULL) {
        PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
        return NULL;
    }

    device = unpack_device(message);
    if (device == NULL) {
        assert(PyErr_Occurred() != NULL);
        Py_DECREF(py_message);
        return NULL;
    }

    is_error = PyDict_SetItemString(py_message, "device", device);
    Py_DECREF(device);

    if (is_error) {
        PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
        Py_DECREF(py_message);
        return NULL;
    }

    lat = unpack_lat(message);
    if (lat != NULL) {
        is_error = PyDict_SetItemString(py_message, "lat", lat);
        Py_DECREF(lat);

        if (is_error) {
            PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
            Py_DECREF(py_message);
            return NULL;
        }
    }

    lon = unpack_lon(message);
    if (lon != NULL) {
        is_error = PyDict_SetItemString(py_message, "lon", lon);
        Py_DECREF(lon);

        if (is_error) {
            PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
            Py_DECREF(py_message);
            return NULL;
        }
    }

    apps = unpack_apps(message);
    if (apps == NULL) {
        assert(PyErr_Occurred() != NULL);
        Py_DECREF(py_message);
        return NULL;
    } 

    is_error = PyDict_SetItemString(py_message, "apps", apps);
    Py_DECREF(apps);

    if (is_error) {
        PyErr_SetString(PyExc_Exception, "Could not create a dict instance.");
        Py_DECREF(py_message);
        return NULL;
    }

    return py_message;
}


/* ======================================================================
   Open file by `path` that must be specified in `args` and
   unpack protobuf messages from the file.

   Returns an iterator of Python dicts (unpacked messages).
*/
static PyObject* py_deviceapps_xread_pb(PyObject* self, PyObject* args) {

    DeviceApps* message;
    gzFile file;
    PyObject* py_message;
    PyObject* list;
    PyObject* iterator;
    const char* path;
    int bytes_read;
    int is_error;
    pbheader_t message_header;

    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    file = gzopen(path, "rb");
    if (file == NULL) {
        PyErr_SetString(PyExc_OSError, "Could not open the file.");
        return NULL;
    }

    list = PyList_New(0);
    if (list == NULL) {
        PyErr_SetString(PyExc_Exception, "Could not create a list instance.");
        gzclose(file);
        return NULL;
    }

    while (1) {
        bytes_read = gzread(file, &message_header, sizeof(message_header));

        if (bytes_read != sizeof(message_header)) {

            if (gzeof(file))
                break;

            PyErr_SetString(PyExc_ValueError, "Invalid format of the file.");
            Py_DECREF(list);
            gzclose(file);
            return NULL;
        }

        if (!(message_header.magic == 0xFFFFFFFF)) {
            PyErr_SetString(PyExc_ValueError, "Invalid format of the file.");
            Py_DECREF(list);
            gzclose(file);
            return NULL;
        }

        uint8_t* buffer = malloc(sizeof(uint8_t) * message_header.length);
        if (buffer == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Could not allocate enough memory.");
            Py_DECREF(list);
            gzclose(file);
            return NULL;
        }

        bytes_read = gzread(file, buffer, message_header.length);

        if (bytes_read != message_header.length) {
            PyErr_SetString(PyExc_ValueError, "Invalid format of the file.");
            Py_DECREF(list);
            gzclose(file);
            free(buffer);
            return NULL;
        }

        // Unpack the message using protobuf-c.
        message = device_apps__unpack(NULL, message_header.length, buffer);
        free(buffer);

        if (message == NULL) {
            PyErr_SetString(PyExc_MemoryError, "Could not unpack message.");
            gzclose(file);
            Py_DECREF(list);
            return NULL;
        }

        py_message = unpack_message(message);
        device_apps__free_unpacked(message, NULL);

        if (py_message == NULL) {
            assert(PyErr_Occurred() != NULL);
            Py_DECREF(list);
            return NULL;
        }

        is_error = PyList_Append(list, py_message);
        Py_DECREF(py_message);

        if (is_error) {
            PyErr_SetString(PyExc_Exception, "Could not create a list instance.");
            Py_DECREF(list);
            gzclose(file);
            return NULL;
        }
    }

    iterator = PySeqIter_New(list);
    Py_DECREF(list);
    gzclose(file);

    return iterator;
}


/* ======================================================================
   Initialize module
*/
static PyMethodDef PBMethods[] = {
    {
        "deviceapps_xwrite_pb", 
        py_deviceapps_xwrite_pb, 
        METH_VARARGS, 
        "Write serialized protobuf to file fro iterator"
    },
    {
        "deviceapps_xread_pb", 
        py_deviceapps_xread_pb, 
        METH_VARARGS, 
        "Deserialize protobuf from file, return iterator"
    },
    {
        NULL, 
        NULL,
        0, 
        NULL
    }
};

static struct PyModuleDef pb =
{
    PyModuleDef_HEAD_INIT,
    /* name of module */
    "pb",
    /* module documentation, may be NULL */
    "",
    /* size of per-interpreter state of the module, or -1 if 
       the module keeps state in global variables. */          
    -1,
    /* defined methods */
    PBMethods
};

PyMODINIT_FUNC PyInit_pb(void)
{
    return PyModule_Create(&pb);
}
