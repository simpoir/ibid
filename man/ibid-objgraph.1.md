% IBID-OBJGRAPH(1) Ibid Multi-protocol Bot | Ibid 0.1
% Stefano Rivera
% March 2010

# NAME

ibid-objgraph - Memory usage graph generation utility for Ibid

# SYNOPSIS

**ibid-objgraph** [*options*...] *logfile* *type*...  
**ibid-objgraph** [*options*...] **-e** *TIME* *logfile*  
**ibid-objgraph** **-h**

# DESCRIPTION

This utility is for graphing object-type usage from an Ibid bot
configured to log such usage.

Matplotlib is required for graphing.

# OPTIONS

**-e** *TIME*, **-\-examine**=*TIME*
:	Examine the object usage at time *TIME*, and print a sorted list of type
	statistics at that time.
	This function can be useful in determining which types to graph, when
	chasing down a detected leak.

**-o** *FILE*, **-\-output**=*FILE*
:	Output to *FILE* instead of displaying interactive graph GUI.
	*FILE* can be any format supported by Matplotlib, detected by the file
	extension.

**-d** *DPI*, **-\-dpi**=*DPI*
:	When outputting in raster formats, use *DPI* output DPI.

**-h**, **-\-help**
	Show a help message and exit.

# FILES

*logfile*
:	A log file generated by loading the **memory** plugin into Ibid, which will
	periodically log object usage.
	It can be gzip compressed, if the filename ends in **.gz**.

# SEE ALSO
`ibid` (1),
`ibid-memgraph` (1),
http://ibid.omnia.za.net/
