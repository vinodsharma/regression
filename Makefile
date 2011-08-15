CFLAGS = `pkg-config --cflags python` `pkg-config --cflags glib-2.0` `pkg-config --cflags pygtk-2.0` -I/usr/local/include/webkit-1.0 `pkg-config --cflags libsoup-2.4` 
LDFLAGS = `pkg-config --libs python` `pkg-config --libs glib-2.0` `pkg-config --libs pygtk-2.0` `pkg-config --libs libsoup-2.4` -L/usr/local/lib -lwebkitgtk-python-1.0 -shared -fPIC 

pywebkitgtk.so: pywebkitgtk.c
	$(CC) $(CFLAGS) $(LDFLAGS) $< -o $@