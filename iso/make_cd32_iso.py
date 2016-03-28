#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iso2cd32
(c) MML, 2012
"""

# Convert an ISO9660 file to an bootable CD32 ISO
#
# The ISO file is built using mkisofs (cdrtools 3.0) with those parameters:
# mkisofs -quiet -V <cd_name> -copyright <your_copyright> -publisher <publisher_name> 
# -o <name.raw> -relaxed-filenames -d -input-charset ASCII -output-charset ASCII 
# -iso-level 3 -A "" -sysid CDTV <folder_name>

import sys
import glob             # glob() expande los patrones de los ficheros en windows
import os               # path.basename(), path.exists()
from optparse import make_option, OptionParser

# List of CDFS options normally set by ISOCD and read by the CD32. Stored one
# byte into the Application Data field of the ISO9660 Primary Volume Descriptor.
# FS     = Fast Search option enabled
# 0x0000 = Size of Fast Search option data
# TM     = TradeMark option
# 0x0014 = Size of TradeMark option data
# 0x00000000 0x00000012 0x00000000 0x00000000 0x00000000
#        = TradeMark option data which contains a block/sector pointer to the
#          CD32.TM file. It's embedded in 0x9000 for not need to add to the disk
#          and not need to search it :P
CDFS_Options = b'\x46\x53\x00\x00\x54\x4d\x00\x14\x00\x00\x00\x00\x00\x00\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
CD32_AppDat = b'\x00' + CDFS_Options + (512 - 1 - len(CDFS_Options)) * b'\x00'
# Procesa la línea de comandos    
def procesar_linea_comandos(linea_de_comandos):
    """
    Devuelve una tupla de dos elementos: (opciones, lista_de_ficheros).
    `linea_de_comandos` es una lista de argumentos, o `None` para ``sys.argv[1:]``.
    """
    if linea_de_comandos is None:
        linea_de_comandos = sys.argv[1:]

    version_programa = "%prog v0.1"
    uso_programa = "usage: %prog [options] file1.raw file2.raw ... fileX.raw"
    descripcion_programa = "%prog transform RAW ISO images to CD32 bootable ISOs."

    # definimos las opciones que soportaremos desde la lnea de comandos
    lista_de_opciones = [make_option("-t", type="string", dest="trademark_fichero", help="trademark file like CD32.TM, CDTV.TM or similar")]
        
    parser = OptionParser(usage=uso_programa, description=descripcion_programa,
        version=version_programa, option_list=lista_de_opciones)
    
    # obtenemos las opciones y la lista de ficheros suministradas al programa
    opciones, lista_ficheros_tmp = parser.parse_args(linea_de_comandos)

    if not opciones.trademark_fichero:
        parser.error("No trademark file specified.")

    # comprobamos el número de argumentos y verificamos los valores
    if not lista_ficheros_tmp:
        parser.error("No files to process.")
    else:
        lista_ficheros = []
        for i in lista_ficheros_tmp:
            lista_ficheros = lista_ficheros + glob.glob(i)

    return opciones, lista_ficheros

# Función principal
def main(linea_de_comandos=None):
    """
    Main function
    """
    # Get commandline arguments
    opciones, lista_ficheros = procesar_linea_comandos(linea_de_comandos)
    
    if not os.path.exists(opciones.trademark_fichero):
        print "Trademark file %s doesn't exist." % opciones.trademark_fichero
        return 1
    with open(opciones.trademark_fichero,"rb") as trademark_fichero:
        trademark = trademark_fichero.read()

    for nombre_fichero in lista_ficheros:
        # Process files
        if not os.path.exists(nombre_fichero):
            print "The file %s doesn't exist." % nombre_fichero
            continue

        # Open file
        iso_tmp = b""
        print "Loading file: " + nombre_fichero
        with open(nombre_fichero,"rb") as fichero:
            iso_tmp = fichero.read()

        # Check l_path_table and m_path_table
        if ord(iso_tmp[0x808C]) != 0x13 and ord(iso_tmp[0x8097]) != 0x15:
            print "Invalid ISO image"
        else:
            # Insert the Application Data Field into the primary volume
            # descriptor which must be at 0x10 * 2048 = 0x8000 and the
            # trademark file into a sector of free space which must be
            # at 0x12 * 2048 = 0x9000.
            iso_tmp = iso_tmp [0: 0x8373] + CD32_AppDat + \
                        iso_tmp [0x8373 + len(CD32_AppDat): 0x9000] + \
                        trademark + iso_tmp [0x9000 + len(trademark):]

            # Save the ISO file
            print "Saving file: " + nombre_fichero.lower().replace(".raw",".iso")
            with open(nombre_fichero.lower().replace(".raw",".iso"),"wb") as fichero:
                fichero.write(iso_tmp)

    return 0    # EXIT_SUCCESS

if __name__ == "__main__":
    estado = main()
    sys.exit(estado)
