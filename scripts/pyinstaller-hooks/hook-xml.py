"""Do not add the unused SAX stack for NetST's ElementTree-only XML use.

PyInstaller's stock ``xml`` hook unconditionally adds SAX readers. NetST parses
GraphML through ``xml.etree.ElementTree`` and never imports SAX.
"""

hiddenimports = []
