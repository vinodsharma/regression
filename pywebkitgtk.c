/*
 * Copyright (C) 2010 Free Software Foundation
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 */

#include <Python.h>
#include <structmember.h>

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <glib.h>
/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>
#include <pygtk/pygtk.h>

#include <webkit/webkit.h>

// #include "pywebkit.h"
typedef PyObject* (*ToPythonFn) (gpointer);

struct pyjoinapi {
    ToPythonFn xhr;
    ToPythonFn win;
    ToPythonFn doc;
};


extern struct pyjoinapi pywebkit_api_fns;

typedef struct {
    PyObject_HEAD
    WebKitWebView    *webview;

} WebViewObject;

static gboolean _webview_repaint_cb(GtkWidget* widget, GdkEventExpose *event,
				    gpointer data);

static void
destroy_cb (GtkWidget* widget, GtkWidget* window)
{
  gtk_main_quit ();
}


static int
WebView_init(WebViewObject *self, PyObject *args, PyObject *kwds)
{
    int width = 800;
    int height = 600;
    gchar *url = NULL;
    GtkWidget* scrolled_window;
    GtkWidget *main_window;

    static char *kwlist[] = {"width", "height", "url", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|iis", kwlist,
                     &width, &height, &url))
        return -1;

    main_window = gtk_window_new (GTK_WINDOW_TOPLEVEL);
    
    gtk_window_set_default_size (GTK_WINDOW (main_window), width, height);
    gtk_widget_set_name (main_window, "pywebkitgtk");
    g_signal_connect (main_window, "destroy", G_CALLBACK (destroy_cb), NULL);
   
    self->webview = WEBKIT_WEB_VIEW (webkit_web_view_new ());
    
    scrolled_window = gtk_scrolled_window_new (NULL, NULL);
    gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled_window),
                                    GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    //gtk_container_add (GTK_CONTAINER (scrolled_window),
    //                  GTK_WIDGET (self->webview));
    //gtk_container_add (GTK_CONTAINER (main_window),
    //                  scrolled_window);
    
    if (url)
      webkit_web_view_load_uri(self->webview, url);

    //gtk_widget_grab_focus (GTK_WIDGET (self->webview));
    //gtk_widget_show_all (main_window);

    return 0;
}

static PyObject *
_webview_get_dom_document(WebViewObject *self, PyObject* unused)
{
    WebKitWebFrame *frame = webkit_web_view_get_main_frame(self->webview);
    gpointer* ptr;
    ptr = webkit_web_frame_get_dom_document(frame);
    return pywebkit_api_fns.doc(ptr);
}

static PyObject *
_webview_get_xml_http_request(WebViewObject *self, PyObject* unused)
{
    WebKitWebFrame *frame = webkit_web_view_get_main_frame(self->webview);
    gpointer* ptr;
    ptr = webkit_web_frame_get_xml_http_request(frame);
    return pywebkit_api_fns.xhr(ptr);
}

static PyObject *
_webview_get_dom_window(WebViewObject *self, PyObject* unused)
{
    WebKitWebFrame *frame = webkit_web_view_get_main_frame(self->webview);
    gpointer* ptr;
    ptr = webkit_web_frame_get_dom_window(frame);
    return pywebkit_api_fns.win(ptr);
}

static void _webview_docloaded_cb(WebKitWebFrame *view, GParamSpec* pspec,
                                  gpointer data)
{
    PyObject* arglist = Py_BuildValue((char*)"()");
    PyObject *callback = (PyObject*)data;

    PyGILState_STATE __py_state;
    __py_state = PyGILState_Ensure();
    PyObject* result = PyObject_CallObject(callback, arglist);
    PyGILState_Release(__py_state);

    Py_DECREF(arglist);

    if (result == NULL) {
        PyErr_Print();
        return; /* Pass error back */
    }
    /* Here maybe use the result */
    Py_DECREF(result);
    return;
}

static gboolean _webview_repaint_cb(GtkWidget* widget, GdkEventExpose *event,
				    gpointer data)
{
  PyObject* arglist = Py_BuildValue((char*)"(iiii)", event->area.x, 
				    event->area.y, event->area.width, 
				    event->area.height);
  PyObject *callback = (PyObject*)data;

  PyGILState_STATE __py_state;
  __py_state = PyGILState_Ensure();
  PyObject* result = PyObject_CallObject(callback, arglist);
  PyGILState_Release(__py_state);

  Py_DECREF(arglist);

  if (result == NULL) {
    PyErr_Print();
    return; /* Pass error back */
  }
  /* Here maybe use the result */
  Py_DECREF(result);
  return false;
}

static PyObject *
_webview_on_webview_doc_loaded(WebViewObject *self, PyObject* args)
{
    PyObject *cb_fn;
    if (!PyArg_ParseTuple(args, "O", &cb_fn))
        return NULL;

    if (cb_fn == Py_None)
        cb_fn = NULL;

    if (cb_fn)
        Py_INCREF(cb_fn);

    g_signal_connect (self->webview, "load-finished", G_CALLBACK (_webview_docloaded_cb), (void*)cb_fn);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
_webview_on_webview_doc_loading(WebViewObject *self, PyObject* args)
{
    PyObject *cb_fn;
    if (!PyArg_ParseTuple(args, "O", &cb_fn))
        return NULL;

    if (cb_fn == Py_None)
        cb_fn = NULL;

    if (cb_fn)
        Py_INCREF(cb_fn);

    g_signal_connect (self->webview, "load-started", G_CALLBACK (_webview_docloaded_cb), (void*)cb_fn);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
_webview_on_webview_repaint(WebViewObject *self, PyObject* args)
{
    PyObject *cb_fn;
    if (!PyArg_ParseTuple(args, "O", &cb_fn))
        return NULL;

    if (cb_fn == Py_None)
        cb_fn = NULL;

    if (cb_fn)
        Py_INCREF(cb_fn);

    g_signal_connect (self->webview, "expose-event", 
		      G_CALLBACK (_webview_repaint_cb), (void *) cb_fn);


    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
_webview_load_document(WebViewObject *self, PyObject* args)
{
    gchar *url = NULL;
    if (!PyArg_ParseTuple(args, "s", &url))
        return NULL;

    webkit_web_view_load_uri(self->webview, url);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * 
_console_message_cb(WebKitWebView *view, gchar *message, gint line, 
              gchar *source_id, gpointer data) {
    //printf("C console message: %s\n",message);
    PyObject *arglist;
    PyObject *my_callback = (PyObject*)data;
    PyObject *result;
    /* Time to call the callback */
    arglist = Py_BuildValue("(s)", message);
    result = PyObject_CallObject(my_callback, arglist);
    Py_DECREF(arglist);
    Py_INCREF(Py_None);
    result = Py_None; 
    return result;

    //printf("console message: %s\n",message);
    //return true;
}

static PyObject *
_script_alert_cb(WebKitWebView *view, WebKitWebFrame *frame, 
            gchar *message,gpointer data) {
    PyObject *arglist;
    PyObject *my_callback = (PyObject*)data;
    PyObject *result;
    /* Time to call the callback */
    arglist = Py_BuildValue("(s)", message);
    result = PyObject_CallObject(my_callback, arglist);
    Py_DECREF(arglist);
    Py_INCREF(Py_None);
    result = Py_None; 
    return result;
    
    //printf("script alert: %s\n",message);
    //return true;
}

static PyObject *
_console_message(WebViewObject *self, PyObject* args)
{
    PyObject *cb_fn;
    if (!PyArg_ParseTuple(args, "O", &cb_fn))
        return NULL;

    if (cb_fn == Py_None)
        cb_fn = NULL;

    if (cb_fn)
        Py_INCREF(cb_fn);

    g_signal_connect (self->webview, "console-message", G_CALLBACK (_console_message_cb), (void*)cb_fn);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
_script_alert(WebViewObject *self, PyObject* args)
{
    PyObject *cb_fn;
    if (!PyArg_ParseTuple(args, "O", &cb_fn))
        return NULL;

    if (cb_fn == Py_None)
        cb_fn = NULL;

    if (cb_fn)
        Py_INCREF(cb_fn);

    g_signal_connect (self->webview, "script-alert", G_CALLBACK (_script_alert_cb), (void*)cb_fn);

    Py_INCREF(Py_None);
    return Py_None;
}
// ececute Java script code
static PyObject *
_webview_ExecuteJs_Script(WebViewObject *self, PyObject* args)
{
    gchar *script = NULL;
    if (!PyArg_ParseTuple(args, "s", &script))
        return NULL;
    webkit_web_view_execute_script(self->webview, script);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef WebView_methods[] = {
    {"LoadDocument", (PyCFunction)_webview_load_document,
                METH_VARARGS,
     PyDoc_STR("Loads Document")},
    {"GetDomDocument", (PyCFunction)_webview_get_dom_document,
                METH_NOARGS,
     PyDoc_STR("Gets DOM Document object")},
    {"GetDomWindow", (PyCFunction)_webview_get_dom_window,
                METH_NOARGS,
     PyDoc_STR("Gets DOM Window object")},
    {"GetXMLHttpRequest", (PyCFunction)_webview_get_xml_http_request,
                METH_NOARGS,
     PyDoc_STR("Gets DOM XMLHttpRequest object")},
    {"SetDocumentLoadedCallback",
     (PyCFunction)_webview_on_webview_doc_loaded,
     METH_VARARGS,
     PyDoc_STR("Sets Document callback function (load done)")},
    {"SetDocumentLoadingCallback",
     (PyCFunction)_webview_on_webview_doc_loading,
     METH_VARARGS,
     PyDoc_STR("Sets Document callback function (load started)")},
    {"SetRepaintCallback",
     (PyCFunction)_webview_on_webview_repaint,
     METH_VARARGS,
     PyDoc_STR("Sets Repaint callback")},
    {"SetConsoleMessageCallback",
     (PyCFunction)_console_message,
            METH_VARARGS,
     PyDoc_STR("Sets console-message handler function")},
    {"SetScriptAlertCallback",
     (PyCFunction)_script_alert,
            METH_VARARGS,
     PyDoc_STR("Sets script-alert handler function")},
    {"ExecuteJsScript",
     (PyCFunction)_webview_ExecuteJs_Script,
            METH_VARARGS,
     PyDoc_STR("Triggers mouse click event")},
    {NULL,  NULL, NULL, NULL},
};


static PyMemberDef WebView_members[] = {
    {NULL}  /* Sentinel */
};


static int
_main (int argc, char* argv[])
{
     gtk_main_quit();

     return 0;
}

static char WebView_doc[] = 
"DirectFB WebView\n";

static PyTypeObject WebViewObjectType = {
    PyObject_HEAD_INIT(NULL)
    0,              /* ob_size           */
    "pywebkitgtk.WebView",            /* tp_name           */
    sizeof(WebViewObject),     /* tp_basicsize      */
    0,              /* tp_itemsize       */
    0,              /* tp_dealloc        */
    0,              /* tp_print          */
    0,              /* tp_getattr        */
    0,              /* tp_setattr        */
    0,              /* tp_compare        */
    0,              /* tp_repr           */
    0,              /* tp_as_number      */
    0,              /* tp_as_sequence    */
    0,              /* tp_as_mapping     */
    0,              /* tp_hash           */
    0,              /* tp_call           */
    0,              /* tp_str            */
    0,              /* tp_getattro       */
    0,              /* tp_setattro       */
    0,              /* tp_as_buffer      */
    Py_TPFLAGS_DEFAULT,     /* tp_flags          */
    WebView_doc,           /* tp_doc            */
    0,              /* tp_traverse       */
    0,              /* tp_clear          */
    0,              /* tp_richcompare    */
    0,              /* tp_weaklistoffset */
    0,              /* tp_iter           */
    0,              /* tp_iternext       */
    WebView_methods,               /* tp_methods        */
    WebView_members,           /* tp_members        */
    0,              /* tp_getset         */
    0,              /* tp_base           */
    0,              /* tp_dict           */
    0,              /* tp_descr_get      */
    0,              /* tp_descr_set      */
    0,              /* tp_dictoffset     */
    (initproc)WebView_init,        /* tp_init           */
};

static char webkitgtk_doc[] = 
"Webkit GTK Python Module (Lorenzo)\n";


static PyMethodDef webkitgtk_methods[] = {
    {NULL, NULL}
};

extern PyMethodDef pywebkit_functions[];
 
void webkit_init_pywebkit(PyObject *m, struct pyjoinapi *api_fns);
 
struct pyjoinapi pywebkit_api_fns;

PyMODINIT_FUNC
initpywebkitgtk(void)
{
    PyObject* m;
    PyObject* d;

    gtk_init(NULL, NULL);
    g_type_init();
    if (!g_thread_supported ())
        g_thread_init(NULL);

    if (!pygobject_init(-1, -1, -1)) {
        PyErr_Print();
        Py_FatalError ("can't initialise module gobject");
    }

    init_pygobject();

    WebViewObjectType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&WebViewObjectType) < 0)
        return;

    m = Py_InitModule3("pywebkitgtk", webkitgtk_methods, webkitgtk_doc);
    if (m == NULL)
        return;

    Py_INCREF(&WebViewObjectType);
    PyModule_AddObject(m, "WebView", (PyObject *)&WebViewObjectType);

    d = PyModule_GetDict (m);
    webkit_init_pywebkit(m, &pywebkit_api_fns);
}


