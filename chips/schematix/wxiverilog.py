#!/usr/bin/env python

import wx
import subprocess
import os
import tempfile
import shelve

try:
    import wx
    import wx.lib.agw.floatspin as FS
except:
    print "You need to install wxpython to run this software"
    exit(0)

import editor
import transcript_window

temp_dir=tempfile.mkdtemp()
wave_file=os.path.join(temp_dir, "wave.lxt")
settings_filename=os.path.join(temp_dir, "settings.v")
object_file=os.path.join(temp_dir, "object")

metric_prefix = {
    "fs" : 1e-15,
    "ps" : 1e-12,
    "ns" : 1e-9,
    "us" : 1e-6,
    "ms" : 1e-3,
    "s" : 1
}

class VerilogProject:
    def __init__(self, files, component, component_selector):
        self.frame = wx.Frame(None, title = "Icarus Verilog", size=(1024,600))

        self.files = files
        self.component = component
        self.top = component["name"]
        self.component_selector = component_selector

        #create menu bar
        #===============
        menubar = wx.MenuBar()
        sim_menu = wx.Menu()
        menubar.Append(sim_menu, "Simulation")
        self.frame.SetMenuBar(menubar)
        splitter = wx.SplitterWindow(self.frame)
        panel = wx.Panel(splitter, -1)

        #Simulation Menu
        #---------------
        self.menu_regenerate_sim = sim_menu.Append(-1, "Regenerate", "Regenerate from Source")
        self.frame.Bind(wx.EVT_MENU, lambda event:self.regenerate_simulation(), self.menu_regenerate_sim)

        self.menu_compile_sim = sim_menu.Append(-1, "Compile", "Compile Simulation")
        self.frame.Bind(wx.EVT_MENU, lambda event:self.compile_simulation(), self.menu_compile_sim)

        self.menu_run_sim = sim_menu.Append(-1, "Run", "Run Simulation")
        self.frame.Bind(wx.EVT_MENU, lambda event:self.run_simulation(), self.menu_run_sim)

        self.menu_view_wave = sim_menu.Append(-1, "View Wave", "Launch GTKWave")
        self.frame.Bind(wx.EVT_MENU, lambda event:self.view_wave(), self.menu_view_wave)

        #create toolbar
        #==============

        self.time_control = wx.SpinCtrl(panel, -1)
        self.time_control.SetRange(1,999)
        self.time_control.SetValue(1)
        self.time_units_control = wx.ComboBox(panel, -1, "us")
        self.time_units_control.Append("fs")
        self.time_units_control.Append("ps")
        self.time_units_control.Append("ns")
        self.time_units_control.Append("us")
        self.time_units_control.Append("ms")
        self.time_units_control.Append("s")
        self.frame.Bind(wx.EVT_COMBOBOX, self.time_changed, self.time_units_control)
        self.frame.Bind(wx.EVT_SPINCTRL, self.time_changed, self.time_control)

        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        toolbar.Add(wx.StaticText(panel, -1, "Run time"), 0, wx.CENTRE)
        toolbar.Add(self.time_control)
        toolbar.Add(self.time_units_control)

        #create file window
        #==================
        self.file_tree = wx.TreeCtrl(panel, -1)
        self.file_tree.Bind(wx.EVT_RIGHT_DOWN, self.show_library_menu)
        self.file_tree.Bind(wx.EVT_LEFT_DCLICK, self.edit)

        #create transcript window
        #========================
        self.transcript = transcript_window.TranscriptWindow(splitter)
        splitter.SplitHorizontally(panel, self.transcript)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(toolbar, 0, wx.EXPAND)
        sizer.Add(self.file_tree, 2, wx.EXPAND)
        panel.SetSizer(sizer)
        self.frame.Show()

        self.frame.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer = wx.Timer(self.frame)
        self.process = None
        self.update_tree()
        self.update_state("start")

    def time_changed(self, event):

        """If the run time changes, we need to recompile"""

        self.update_state("start")

    def update_state(self, state):

        """Keep track of the simualtor state"""

        self.state = state
        if state == "start":

            self.menu_compile_sim.Enable(True)
            self.menu_run_sim.Enable(False)
            self.menu_view_wave.Enable(False)

        elif state == "sim_compiled":

            self.menu_compile_sim.Enable(True)
            self.menu_run_sim.Enable(True)
            self.menu_view_wave.Enable(False)

        elif state == "sim_run":

            self.menu_compile_sim.Enable(True)
            self.menu_run_sim.Enable(True)
            self.menu_view_wave.Enable(True)

    def show_library_menu(self, event):

        """Show a context menu if a file is right clicked"""

        pt = event.GetPosition();
        item, flags = self.file_tree.HitTest(pt)
        if self.file_tree.GetPyData(item) == "file":
            label = self.file_tree.GetItemText(item)
            filename = label
            file_node = item
            popupmenu = wx.Menu()
            edit_source = popupmenu.Append(-1, "Open")
            self.frame.Bind(wx.EVT_MENU, lambda event: editor.open_file(filename), edit_source)
            self.frame.PopupMenu(popupmenu)

    def edit(self, event):

        """Edit file when double clicked"""

        pt = event.GetPosition();
        item, flags = self.file_tree.HitTest(pt)
        if self.file_tree.GetPyData(item) == "file":
            label = self.file_tree.GetItemText(item)
            filename = label
            editor.open_file(filename)
     
    def update_tree(self):

        """Add files to the file tree"""

        self.file_tree.DeleteAllItems()
        root = self.file_tree.AddRoot("Files")
        for path in self.files:
            node = self.file_tree.AppendItem(root, path)
            self.file_tree.SetPyData(node, "file")
        self.file_tree.ExpandAll()

    def check_icarus_installed(self):

        """Check that Icarus Verilog is correctly installed"""

        try:
            subprocess.call("iverilog")
            return True
        except OSError:
            self.transcript.log("Icarus Verilog does not appear to be installed correctly.")
            self.transcript.log("Get Icarus Verilog from http://iverilog.icarus.com")
            return False

    def check_gtkwave_installed(self):

        """Check that Icarus Verilog is correctly installed"""

        try:
            subprocess.call("gtkwave -h", shell=True)
            return True
        except OSError:
            self.transcript.log("GTK Wave does not appear to be installed correctly.")
            self.transcript.log("Get GTKWave from http://gtkwave.sourceforge.net")
            return False

    def regenerate_simulation(self):

        """Regenerate all components and start everything from scratch"""

        self.update_state("start")
        self.component_selector.update()
        self.component_selector.transcript.log("Generating all dependencies")
        self.component_selector.generate_dependencies(self.component)
        self.component_selector.transcript.log("Creating file list")
        file_list = []
        for dependency in self.component_selector.get_dependencies(self.component):
            file_list.append(self.component_selector.get_component_path(dependency))
        self.files = file_list
        self.update_tree()
        self.component_selector.transcript.log("Launching Verilog simulator")

    def compile_simulation(self):

        """Compile a simulation using """

        if not self.check_icarus_installed():
            return

        self.transcript.log("launching icarus verilog compiler\n")

        #calculate run time
        time_to_run = self.time_control.GetValue() * metric_prefix[
            self.time_units_control.GetValue()]
        print time_to_run

        #create a settings file for iverilog
        settings_file = open(settings_filename, "w")
        settings_file.write(
"""
`timescale 1s/1ps
module settings();
 initial begin
	 $dumpfile("%s");
	 $dumpvars(0, %s);
 end
 initial begin
	 #%s
	 $finish();
 end
endmodule"""%(wave_file, self.top, time_to_run)
        )
        settings_file.close()

        for path in self.files:
            self.transcript.log("compiling: %s\n"%path)

        command = 'iverilog -o {0} {1} {2}'.format(
                object_file,
                settings_filename,
                " ".join(self.files))

        process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                shell=True)

        for line in process.stdout:
            self.transcript.log(line)

        process.wait()

        if process.returncode == 0:
            self.update_state("sim_compiled")
            self.transcript.log("Icarus Verilog compile ... successful\n")
        else:
            self.update_state("start")
            self.transcript.log("Icarus Verilog compile ... failed\n")

    def run_simulation(self):

        """Run a simulation using Icarus Verilog"""

        self.transcript.log("launching Icarus Verilog simulation\n")
        command = "vvp {0} -lxt2".format(
                object_file,
        )
        self.process = subprocess.Popen(command, 
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True)
        self.timer.Start(100)

    def on_timer(self, event):

        """We don't want the simulator to lock the GUI"""

        try:
            for i in range(100):
                line = next(self.process.stdout)
                self.transcript.log(line)
        except StopIteration:
            self.timer.Stop()
            self.process.wait()
            if self.process.returncode == 0:
                self.update_state("sim_run")
                self.transcript.log("Icarus Verilog simulation ... successful\n")
            else:
                self.update_state("sim_run")
                self.transcript.log("Icarus Verilog simulation ... failed\n")

    def view_wave(self):

        """Open simulation waveform in GTKWave"""
        if not self.check_gtkwave_installed():
            return

        self.transcript.log("launching GTKWave waveform viewer\n")
        subprocess.Popen("gtkwave {0}".format(wave_file), shell=True)
        

if __name__ == "__main__":
    app = wx.App()
    VerilogProject()
    app.MainLoop()
