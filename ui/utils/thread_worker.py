import threading
import traceback
import customtkinter as ctk

class ThreadWorker:
    """
    A utility class to run heavy tasks in the background without blocking the CustomTkinter UI.
    It takes a target function and callbacks for success, error, and completion.
    Callbacks are automatically scheduled to run on the main UI thread using master.after(0, ...)
    """
    def __init__(self, master, target, args=(), kwargs=None, on_success=None, on_error=None, on_complete=None):
        self.master = master
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.on_success = on_success
        self.on_error = on_error
        self.on_complete = on_complete
        
        # Start the background thread
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def _run(self):
        try:
            result = self.target(*self.args, **self.kwargs)
            # Schedule the success callback on the main UI thread if master still exists
            if self.on_success:
                self._safe_schedule(self.on_success, result)
        except Exception as e:
            traceback.print_exc()
            if self.on_error:
                self._safe_schedule(self.on_error, str(e))
        finally:
            if self.on_complete:
                self._safe_schedule(self.on_complete)

    def _safe_schedule(self, callback, *args):
        """Safely schedule a callback on the UI thread."""
        try:
            # Check if master widget still exists before scheduling
            if self.master.winfo_exists():
                self.master.after(0, lambda: self._execute_if_alive(callback, *args))
        except (AttributeError, RuntimeError, ctk.TclError):
            pass

    def _execute_if_alive(self, callback, *args):
        """Execute callback only if the master widget is still alive."""
        try:
            if self.master.winfo_exists():
                callback(*args)
        except (AttributeError, RuntimeError, ctk.TclError):
            pass
