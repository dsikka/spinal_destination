cmake_minimum_required(VERSION 3.5)

project(spinal_distination_2)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/spinal_distination_2")
set(EXTENSION_CATEGORY "Surgical Navigation")
set(EXTENSION_CONTRIBUTORS "Sam (STDS)")
set(EXTENSION_DESCRIPTION "Fill this in later.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/spinal_distination_2.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/spinal_distination_2/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(display)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
