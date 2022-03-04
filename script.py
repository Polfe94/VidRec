import os
import PySpin
import sys

'''CONFIG'''
_path = '/path/to/save/data/to'

'''CAM DICTIONARY'''
# key is the order, from topleft to bottom right
# the value is the serial number of the cam
_CamArray = {
    0: '17215390',
    1: '17215425',
    2: '17179428',
    3: '17215392',
    4: '17179427',
    5: '17215395',
    6: '17215394',
    7: '17215423',
    8: '17215421',
    9: '17215382',
    10: '17215420',
    11: '17215424 '
}


'''CODE'''

'''HERE IT WOULD BE GOOD TO CONTROL THE NUMBER OF CAMERAS'''
# Set camera serial numbers
SerialNums = list(_CamArray.values())
# Get system
system = PySpin.System.GetInstance()
 
# Get camera list
cam_list = system.GetCameras()


if len(cam_list) > 1:

    cams = []
    
    # Get cameras by serial and initialize
    for i in range(len(SerialNums)):
        cams.append(cam_list.GetBySerial(SerialNums[i]))
        cams[i].Init()
        cams[0].AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame)

    # Set primary camera
    cams[0].LineSelector.SetValue(PySpin.LineSelector_Line2)
    cams[0].V3_3Enable.SetValue(True)

    # Set secondary cameras
    for cam in cams[1::]:
        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        cam.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)

elif len(cam_list) == 1:
    cams = cam_list[0]

else:
    # might as well be that no cameras are connected ??
    print('Error, no cameras were selected to record!')

'''MAIN LOOP'''


for cam in cams:
    cam.BeginAcquisition()
    img = cam.GetNextImage(100)
    img.Save()
    img.Release()

 
# Start acquisition; note that secondary cameras have to be started first so acquisition of primary camera triggers secondary cameras.
cam_2.BeginAcquisition()
cam_3.BeginAcquisition()
cam_1.BeginAcquisition()
 
# Acquire images
image_1 = cam_1.GetNextImage()
image_2 = cam_2.GetNextImage()
image_3 = cam_3.GetNextImage()
 
# Save images
image_1.Save('cam_1.png')
image_2.Save('cam_2.png')
image_3.Save('cam_3.png')
 
# Release images
image_1.Release()
image_2.Release()
image_3.Release()
 
# end acquisition
cam_1.EndAcquisition()
cam_2.EndAcquisition()
cam_3.EndAcquisition()







NUM_IMAGES = 10  # number of images to grab




def acquire_images(cam, nodemap, nodemap_tldevice):

    try:
        result = True

        # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        print('Acquisition mode set to continuous...')

        #  Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        print('Acquiring images...')

        #  Retrieve device serial number for filename
        #
        #  *** NOTES ***
        #  The device serial number is retrieved in order to keep cameras from
        #  overwriting one another. Grabbing image IDs could also accomplish
        #  this.
        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)

        # Retrieve, convert, and save images
        for i in range(NUM_IMAGES):
            try:

                # get image with a timeout of 1000 miliseconds
                image_result = cam.GetNextImage(1000)

                ## HERE IT WOULD BE INTERESTING TO DISCARD ALL IMAGES FROM THE POOL
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

                else:
                    
                    # convert image to color (BGR 8)
                    image_converted = image_result.Convert(PySpin.PixelFormat_BGR8, PySpin.NEAREST_NEIGHBOR)

                    # Create a unique filename
                    if device_serial_number:
                        filename = 'Acquisition-%s-%d.jpg' % (device_serial_number, i)
                    else:  # if serial number is empty
                        filename = 'Acquisition-%d.jpg' % i

                    image_converted.Save(filename)
                    print('Image saved at %s' % filename)

                    image_result.Release()
                    print('')

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                return False

        cam.EndAcquisition()
    
    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def print_device_info(nodemap):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        result &= print_device_info(nodemap_tldevice)

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Acquire images
        result &= acquire_images(cam, nodemap, nodemap_tldevice)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def main():
    """
    Example entry point; please see Enumeration example for more in-depth
    comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # Since this application saves images in the current folder
    # we must ensure that we have permission to write to this folder.
    # If we do not have permission, fail right away.
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return False

    test_file.close()
    os.remove(test_file.name)

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Run example on each camera
    for i, cam in enumerate(cam_list):

        print('Running example for camera %d...' % i)

        result &= run_single_camera(cam)
        print('Camera %d example complete... \n' % i)

    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input('Done! Press Enter to exit...')
    return result

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
