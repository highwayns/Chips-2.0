//name: discard
//tag: schematic
//input: in1 : bits
//source_file: built_in
//parameter: bits : 16

///Discard
///=======
///
///Discard all data on *in1*. Useful to avoid unconnected outputs.
///
///::
///
///    null <= in1
///
///..
///
/// +--------------------+-------------------------------------+
/// |Language            | Verilog                             |
/// +--------------------+-------------------------------------+
/// |Synthesis           | Yes                                 |
/// +--------------------+-------------------------------------+
/// |License             | MIT                                 |
/// +--------------------+-------------------------------------+
/// |Author              | Jonathan P Dawson                   |
/// +--------------------+-------------------------------------+
/// |Copyright           | Jonathan P Dawson 2013              |
/// +--------------------+-------------------------------------+
///
///Parameters
///----------
///
/// ============= ============== ==============================================
/// Name          Type           Description
/// ============= ============== ==============================================
/// bits          integer        Data width of in1.
/// ============= ============== ==============================================
///
///Inputs
///------
///
/// ============= ============== ==============================================
/// Name          Width          Description
/// ============= ============== ==============================================
/// in1           bits           Input Stream
/// ============= ============== ==============================================
///

module discard #(

    parameter bits=16

) (

    input clk,
    input rst,
   
    input [bits-1:0] in1,
    input in1_stb,
    output in1_ack

);

  assign in1_ack = 1'b1;

endmodule
