#include <Python.h>
#include <stdbool.h>

/* Will come from go */
PyObject* parse_demo(PyObject* , PyObject*);

/* To shim go's missing variadic function support */
int PyArg_ParseTuple_parse_demo(
    PyObject* args,
    char* dem_path,
    int parse_rate,
    bool parse_frames,
    int64_t trade_time,
    char* round_buy,
    bool damages_rolled,
    char* demo_id,
    bool json_indentation,
    char* outpath
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
