#include <Python.h>
#include <stdbool.h>

/* PT: Based on https://github.com/asottile/setuptools-golang-examples/blob/master/sum_go/sum_go.c
   We are creating a python c extension with the PyInit_wrapper() call and related entities.
   As go and c and co-compatible, we can use this c interface to drive the go parser library.
   
   PyArg_ParseTuple_parse_demo() is used to convert the python C.PyObject* args to native c types and pass
   them back to the calling go function.
   
   On the Go side, we can then convert these native c types to go types, and proceed from there.
   
   PyArg_ParseTuple() (https://docs.python.org/3/c-api/arg.html#c.PyArg_ParseTuple) takes the args object
   and the native c types, with a format string to inform it how to convert from the args tuple to the native
   c types.  Info about the format string can be found here https://docs.python.org/3/c-api/arg.html#parsing-arguments
*/

/* Will come from go */
PyObject* parse_demo(PyObject* , PyObject*);

/* To shim go's missing variadic function support */
int PyArg_ParseTuple_parse_demo(
    PyObject* args,
    char** dem_path,
    int* parse_rate,
    bool* parse_frames,
    int64_t* trade_time,
    char** round_buy,
    bool* damages_rolled,
    char** demo_id,
    bool* json_indentation,
    char** outpath
) {
    return PyArg_ParseTuple(
        args, "sbpLspsps", dem_path, parse_rate,
        parse_frames, trade_time, round_buy, damages_rolled,
        demo_id, json_indentation, outpath
    );
}

static struct PyMethodDef methods[] = {
    {"parse", (PyCFunction)parse_demo, METH_VARARGS},
    {NULL, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "wrapper",
    NULL,
    -1,
    methods
};

PyMODINIT_FUNC PyInit_wrapper(void) {
    return PyModule_Create(&module);
}
