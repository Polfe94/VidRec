import sys, getopt, os
import re

def argparse(argv):

    error_msg_rec = 'Recruitment misspecified ! Check possible options in help or params.py'
    error_msg_float = 'Parameter must be a float number !'
    error_msg_int = 'Parameter must be an integer !'
    error_msg_bool = 'Parameter must be a boolean !'
    wrng_msg_1 = 'Leaving default parameter value ...'
    wrng_msg_2 = 'Exiting program ...'

    def _help():
        print('+++ AVAILABLE PARAMETERS +++')
        print('\t -p o --params to change camera parameters')
        print('\t\t Must be a key-value pair, i.e. "-p exposure=10"')
        print('\t\t Can be a list of parameters, separated by a semicolon, i.e. "-p exposure=10;gain=5"')
        print('\t\t Pass either a single value, or a value for each camera')
        print('\t\t\t "-p exposure=10,11,12,10.5" will work for 4 cameras')
        print('\t\t\t "-p exposure=10" will set exposure = 10 to all cameras')
        print('\t\t Currently supported parameters are exposure and gain')
        print('\n')
        print('\n')
        # print('\t -r or --resolution changes the output resolution by a factor')
        # print('\t\t It will be applied as VALUE * (4000, 3000)')
        # print('\t\t -r or --resolution 0.5 will set the resolution to be (2000, 1500)')
        # print('\n')
        # print('\n')
        print('\t --fps will set frames per second (FPS) to the provided value')
        print('\t\t --fps 15 sets recording to 15 FPS')
        print('\t\t --fps 0.2 sets recording FPS to 0.2 (i.e. an image every 5 seconds)')
        print('\t\t Divisions also work, i.e. --fps 1/300 (take an image every 5 minutes)')
        print('\t\t FPS are capped to camera speed')
        print('\n')
        print('\n')
        # print('\t -v or --video to record video')
        # print('\t\t -v True or --video True (default) records video and destroys individual images')
        # print('\t\t -v False or --video False keeps individual images and does not append them to a video')
        # print('\n')
        # print('\n')       
        print('\t --filename to set a folder to store the video or images')
        print('\t\t Either full path or relative path to the folder the video (or images) should be saved into')
        print('\t\t If the folder does not exists, and the directory is valid, a folder will be created')
        print('\n')
        print('\n')
        print('+++ HELP ENDS HERE, PRESS ENTER TO EXIT...')
        input()
        sys.exit(0)


    
    try:

        if '-h' in argv or '--help' in argv:
            print(_help())

        else:
            mods = {}

        opts, args = getopt.getopt(argv, '',
        # ["params=", "fps=", "filename=", "video=", "resolution="])
        ["params=", "fps=", "filename=", "directory="])

    except getopt.GetoptError:
        print('Something went wrong ! Try typing -h or --help to see possible parameters.')
        print(wrng_msg_2)
        sys.exit(2)

    for opt, arg in opts:

        if opt in ('--params'):
            paramlist = arg.split(';')

            for param in paramlist:
                param = param.split('=')

                mods[param] = []

                if hasattr(globals()['params'], param[0]):
                    try:
                        setattr(globals()['params'], param[0], float(param[1]))
                    except:
                        print(error_msg_float)
                        print(wrng_msg_1)
                
                else:
                    print('Parameter ' + str(param[0]) + ' is not a valid parameter!')
                    print(wrng_msg_1)
        

        if opt in ('--filename'):

            path = arg.split('~')
            if len(path) == 2:
                path = os.path.expanduser('~') + os.sep + path[1]

            elif len(path) == 1:
                path = path[0]

            else:
                path = ''.join(path)

            if os.path.exists(path):
                mods['vidPath'] = path

            else:
                splt_os = path.split(os.sep)
                splt = path.split('/')


                if len(splt) < len(splt_os):
                    used_path = splt_os

                else:
                    used_path = splt

                if os.path.exists(''.join(used_path[:-1])):
                    os.mkdir(path)
                    mods['vidPath'] = path

                else:
                    print('Could not find %s' % path)
                    print(wrng_msg_1)


        # if opt in ('--resolution'):
        #     mods['resize'] = arg

        if opt in ('-d', '--directory'):

            path = arg.split('~')
            if len(path) == 2:
                path = os.path.expanduser('~') + os.sep + path[1]

            elif len(path) == 1:
                path = path[0]

            else:
                path = ''.join(path)

            try:

                splt = arg.split('/')
                if len(splt) == 1:
                    globals()['params'].folder = str(params.path) + str(arg)
                    print('Set results directory to: ' + str(params.path) + str(arg))

                else:
                    if splt[-1] == '':
                        splt = splt[:-1]
                    
                    if len(splt) == 1:
                            globals()['params'].folder = str(params.path) + str(arg)
                            print('Set results directory to: ' + str(params.path) + str(arg))
                    else:
                        globals()['params'].folder = '/'.join(splt) + '/'
                        print('Set results directory to: ' + '/'.join(splt) + '/')
            
            except:

                print('Something went wrong !!!')
                print(wrng_msg_1)

        