import xml.etree.ElementTree as ET

def print_xml(elem: ET.Element):
    ET.indent(elem, space="  ")
    elem_xml_str = ET.tostring(elem, encoding="unicode")
    print(elem_xml_str.strip())
    return