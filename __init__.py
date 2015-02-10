from functools import partial #for buttons
import maya.cmds as cmds
import spaces as sp #for... everything
import os as os #for saving to file
import json #for reading/writing file format

class SpacesError(Exception):
    pass

    # ---- SPACE DATA ---- #
class spaceData(object):

    #read file
    def __init__(self):

        self.dir = None #directory of file
        self.path = None #location of file
        self.data = None #file data
        #default content
        self.default = {'linear' : [ [0.0,0.0,0.0,45.0] , [1.0,1.0,45.0,0.0] ],
                        'flat' : [ [0.0,0.0,0.0,0.0] , [1.0,1.0,0.0,0.0] ],
                        'swish' : [ [0.0,0.0,0.0,60.0] , [1.0,1.0,60.0,0.0] ],
                        'free fall' : [ [0.0,0.0,0.0,55.0] , [0.5,0.75,48.0,48.0], [1.0,1.0,0.0,0.0] ],
                        'saw': [[0.0, 0.0, 0.0, 0.21], [0.2, 0.1, 46.0, 46.0], [1.0, 1.0, 46.0, 0.0] ],
                        'jump': [[0.0, 0.0, 0.0, 0.0], [0.17, 0.2, 70.0, 70.0], [0.5, 0.88, 33.0, 33.0], [1.0, 1.0, 0.0, 0.0]]
                        }


        filename = 'Space_Data.txt'
        (self.dir, throwaway) = os.path.split(sp.__file__)
        self.dir = os.path.join(self.dir, 'spaceGUI_icons')
        if not os.path.isdir(self.dir):
        	raise SpacesError( 'Hold on a second there cowboy. There is no folder named "spaceGUI_icons" in your script directory.')
        self.path = os.path.join(self.dir,filename)
        self.load()

    #load data
    def load(self):
        if os.path.isfile(self.path):
            with open(self.path, 'r') as store:
                try:
                    self.data = json.load(store)
                except:
                    print 'Trouble opening Data file. Only loading default Spaces.'
                    self.data = self.default
        else:
            print "Data file doesn't exist. Creating."
            store = open(self.path, 'w')
            store.write(json.dumps(self.default))
            store.close()
            self.data = self.default
    #put data to file
    def write(self):
        try:
            with open( self.path, 'w') as store:
                json.dump( self.data, store)
            return True
        except:
            return False

    # ---- SPACE  GUI ---- #
#running the GUI
class spaceGUI(object):
    def __init__(self):
    	self.pane = None #gui window
    	self.store = None #data from file
    	self.lastname = None #last recorded name
    	self.message = None #status message
    	self.jobs = {} #list of running script jobs

    	self.selectjob = None #last attribute selected
    	self.selecttime = None#current time on slider - ensure time changes don't affect selection

    	self.selectkeys = None #list of selected keys
    	self.selectspaces = None #list of selected keys corresponding spaces

    	self.flip = False #flip checkbox
    	self.mirror = False #mirror tangent
    	self.autoselect = False#auto deselect breakdowns
    	self.record = True#make sure we're not recording True means not recording
    	self.recordcheck = None #checkbox

        self.store = spaceData()
        #GUI
        self.pane = cmds.window( title = 'Spaces', rtf= True, sizeable = False)
        cmds.columnLayout( adjustableColumn=True )
        cmds.gridLayout( numberOfColumns=3, cellWidthHeight= (80,80) )
        for obj in self.store.data:
            obj = obj.title()
            cmds.frameLayout( label = obj, lv=False)
            cmds.symbolButton( image=self._findImage(obj), command = partial(self._placekeys, obj ), height=55 )
            cmds.button( label = obj, command = partial(self._placekeys, obj ), height=25 )
            cmds.setParent('..')
        cmds.setParent('..')
        cmds.gridLayout( numberOfColumns=2, cellWidthHeight= (120,20) )
        cmds.checkBox( label='Invert' , changeCommand = partial(self._checkupdate, 'flip'))
        self.recordcheck = cmds.checkBox( label='Preserve Spaces' , changeCommand = partial(self._checkupdate, 'autoselect'))
        cmds.checkBox( label='Mirror' , changeCommand = partial(self._checkupdate, 'mirror'))
        cmds.text( label = "(Experimental)" )
        cmds.setParent('..')
        cmds.separator()
        cmds.setParent('..')
        cmds.frameLayout( label = 'Record a new Space', cll = True, cl= True, ec= partial(self._checkupdate, 'record', False), cc = partial(self._checkupdate, 'record', True) )
        self.message = cmds.text( label='Insert a name for your Space.' )
        self.lastname = cmds.textField( aie=True, ec=self._storespace, height=30 )
        cmds.button( label = 'Record Space' , command = self._storespace , height= 50 )
        cmds.button( label = 'DELETE Space' , command = self._deletespace , height= 20 )
        cmds.setParent('..')
        cmds.showWindow( self.pane )

        #setup scriptjob on selection change.
        self.jobs['deselect'] = [cmds.scriptJob( e= ['SelectionChanged', self._selectionChange], cu=True )]
        #run cleanup when window closed
        cmds.scriptJob( uid = [ self.pane , self._cleanup ] )

    def _webpage(self):
        import webbrowser
        webbrowser.open('http://internetimagery.com/news/spaces-maya/')

    #track changes to attribute
    def _attrchange(self, index, listname, *args):

        if self.autoselect and self.record: #make sure we have preserve spaces active
            checktime = cmds.currentTime(query = True)
            if checktime == self.selecttime: #check time slider hasn't moved
                cmds.undoInfo( openChunk = True)
                newkeys = self._getSelectedKeys()
                if self.selectspaces and self.selectkeys:
                    if self._compareChanges(newkeys, self.selectkeys):
                        print index, ' Auto updates since refresh. '
                        for obj in newkeys:
                            for attr in newkeys[obj]:
                                keys = newkeys[obj][attr]
                                for key in range(len(keys)-1):
                                    time = keys[key][0]
                                    keylist = self.selectspaces[obj][attr][key]
                                    selection = sp.Space( time, {obj:{attr:[]}}) #reinstate the curves
                                    selection.clear()
                                    selection.insert(keylist)
                self.selectkeys = newkeys #get list of key times
                self.selectspaces = self._recordAll(self.selectkeys) #get list of spaces
                cmds.undoInfo( closeChunk = True)
            else:
                self.selecttime = checktime

            #recreate script job
            if self.selectkeys:
                obj = self.selectkeys.keys()
                attr = self.selectkeys[ obj[0] ].keys()
                node = obj[0]+'.'+attr[0]
                nextindex = len(self.jobs[listname])
                self.jobs[listname].append( cmds.scriptJob( ro = True, ac = [node, partial(self._attrchange, nextindex, listname)]) )


    #compare if the two lists are the same
    def _compareChanges(self, list1, list2 ):
        same = True
        if list1 and list2:
            try:
                for obj in list1:
                    for attr in list1[obj]:
                        for key in range(len(list1[obj][attr])):
                            new = list1[obj][attr][key]
                            old = list2[obj][attr][key]
                            if same:
                                if not (new[0] == old[0] and (old[1]-0.001) < new[1] < (old[1]+0.001)): #check that things have actually changed
                                    same = False
                if not same:
                    return True
            except:
                print 'Failed to compare lists...'
                return False
        return False

    #remove any breakdowns from selection
    def _selectionChange(self):
        #clear out any existing attribute value events
        listname = 'attribute'
        if listname in self.jobs:
            if self.jobs[listname]:
                for job in self.jobs[listname]:
                    self._cleanjob( job )
                self.jobs[listname] = []
        else:
            self.jobs[listname] = []

        if self.autoselect and self.record:
            self.selectkeys = self._getSelectedKeys()
            self.selectspaces = self._recordAll(self.selectkeys)
            self.selecttime = cmds.currentTime(query = True)
            if self.selectkeys:
                obj = self.selectkeys.keys()
                attr = self.selectkeys[ obj[0] ].keys()
                node = obj[0]+'.'+attr[0]
                nextindex = len(self.jobs[listname])
                self.jobs[listname].append( cmds.scriptJob( ro = True, ac = [node, partial( self._attrchange, nextindex, listname ) ] ) )


    #format a list of keys selected, ignoring and deslecting breakdowns. expanding selection one key back and removing last key of curve
    def _getSelectedKeys(self):
        objects = cmds.ls( selection = True )
        if objects:
            selection = {}
            for obj in objects:
                channel = cmds.keyframe( obj, query=True, name=True, sl=True)
                attribute = {}
                if channel:
                    for chan in channel:
                        split = chan.rpartition('_')
                        attr = split[-1]
                        keys = cmds.keyframe( obj, at=attr,  query = True )#grab whole curve
                        keylist = []
                        if keys:
                            for key in range(len(keys)):
                                breakdown = cmds.keyframe( obj, at=attr, time= ( keys[key] , keys[key] ), query = True, bd = True )
                                if breakdown:
                                    cmds.selectKey( obj, at=attr, time = (keys[key],keys[key]), rm=True )
                                else:
                                    value = cmds.keyframe( obj, at=attr, time=( keys[key] , keys[key] ), query=True, vc=True)
                                    keylist.append( [ keys[key], value[0] ] )
                        if len(keylist) > 0:
                            attribute[attr] = keylist
                if attribute:
                    selection[obj] = attribute
            if selection:
                return selection
        return False

    #find non-breakdown key
    def _findPrev(self, time, obj, attr, direction):
        time = cmds.findKeyframe( obj, at=attr, which=direction, time=(time,time))
        if cmds.keyframe( obj, at=attr, query=True, bd=True, time=(time,time) ):
            time = self._findPrev( time, obj, attr, direction)
        return time

    #record everything from keylist
    def _recordAll(self, keylist):
        if keylist:
            newobj = {}
            for obj in keylist:
                newattr = {}
                for attr in keylist[obj]:
                    newkeys = []
                    selection = { obj: { attr: [] } } #selection format for Space class
                    for key in range( len( keylist[obj][attr] )-1 ):
                        data = sp.Space( keylist[obj][attr][key][0], selection ).extract(True)
                        if data:
                            newkeys.append(data)
                    if newkeys:
                        newattr[attr] = newkeys
                if newattr:
                    newobj[obj] = newattr
            if newobj:
                return newobj
        return False


    #remove ALL outstanding jobs
    def _cleanup(self):
        if self.jobs:
            for job in self.jobs:
                for jobID in self.jobs[job]:
                    if jobID:
                        self._cleanjob(jobID)
            self.jobs = {}

    def _cleanjob(self, job):
        if cmds.scriptJob( exists = job ):
            print 'clean', job
            cmds.scriptJob ( kill=job )
            return True
        return False

    #update checkboxes
    def _checkupdate(self, *label):
        if label[0] == 'flip':
            self.flip = label[1]
        elif label[0] == 'mirror':
                self.mirror = label[1]
        elif label[0] == 'autoselect':
                self.autoselect = label[1]
                if self.autoselect:
                    self._selectionChange()
        elif label[0] == 'record':
                self.record = label[1]
                cmds.checkBox( self.recordcheck, edit= True, enable = label[1] )

    #delete space
    def _deletespace(self, thing):
        name = cmds.textField(self.lastname, query=True, tx=True).strip().lower()
        if name:
            if name in self.store.data:
                #get data again to be sure nothing has changed
                self.store.load()
                if self.store.data.pop(name):
                    if self.store.write():
                        cmds.text( self.message, edit = True, label = 'Curve Deleted successfully.' )
                        return True

        cmds.text( self.message, edit=True, label = 'Curve name not found.' )
        return False
    #save space
    def _storespace(self, blah):
        #grab name / check if one is there
        name = cmds.textField(self.lastname, query=True, tx=True).strip().lower()
        if name:
            if name not in self.store.data:
                keylist = cmds.keyframe( query=True, sl=True )
                channel = cmds.keyframe( query=True, name=True)
                if keylist and len(keylist) > 1:
                    if len(channel) == 1:
                        cmds.selectKey( clear = True )
                        cmds.keyframe( channel, edit=True, bd = False, time = (keylist[0],keylist[-1]) )
                        cmds.keyframe( channel, edit=True, bd = True, time = ((keylist[0]+0.1),(keylist[-1]-0.1)) )
                        cmds.selectKey( channel, time=(keylist[0],keylist[-1]) )
                        if self._savespace(keylist[0],name):
                            cmds.text( self.message, edit=True, label = 'Curve added! Close and reopen.' )
                        else:
                            cmds.text( self.message, edit=True, label = "Something went wrong. Try again? :'(" )
                    else:
                        cmds.text( self.message, edit=True, label = 'Make sure only one curve is selected.' )
                else:
                    cmds.text( self.message, edit=True, label = 'Select the keys that form your curve.' )
            else:
                cmds.text( self.message, edit=True, label = 'A curve with that name already exists.' )
        else:
            cmds.text( self.message, edit=True, label = 'Each curve requires a name.' )
            return False
        #print sp.Space().extract(True)
    #store the space in file
    def _savespace(self, time, name):
        keylist = sp.Space(time).extract(True)
        if keylist:
            #get data again to be sure nothing has changed
            self.store.load()
            self.store.data[name] = keylist
            if self.store.write():
                return True
        return False

    #get button image
    def _findImage(self, name):
        filename = name+'.bmp'
        path = os.path.join(self.store.dir , filename)
        if os.path.isfile(path):
            return path
        else:
            return os.path.join(self.store.dir,'custom.bmp')

    #when button is pushed
    def _placekeys(self, label, throwaway):
        selection = sp.Space()
        label = label.lower()
        #copy list values to not modify original
        keylist = []
        for key in self.store.data[label]:
            keylist.append( key[:] )
        if self.flip:
            keylist = self._invertKeys(keylist)
        if self.mirror:
            keylist = self._mirror(keylist)
        selection.clear()
        if selection.insert(keylist):
            print 'Space inserted.'
        else:
            return False
    #mirror keys
    def _mirror(self, keylist):
        #copy keylist twice
        newkeylist1 = []
        newkeylist2 = []
        for key in keylist:
            newkeylist1.append(key[:])
            newkeylist2.append(key[:])
        #invert second keylist
        newkeylist2 = self._invertKeys(newkeylist2)
        newkeylist1[-1][3] = newkeylist1[-1][2]
        #add 1 to newkeys values
        for i in range(len(newkeylist2)-1):
            i += 1
            newkeylist2[i][0] += 1
            newkeylist2[i][1] += 1
            newkeylist1.append(newkeylist2[i][:])

        #scale back to fit
        for key in newkeylist1:
            key[0] *= 0.5
            key[1] *= 0.5
        return newkeylist1

    #invert the keys
    def _invertKeys(self, keylist):
        #swap border tangents
        temp = keylist[0][3]
        keylist[0][3] = keylist[-1][2]
        #keylist[0][0] = 1.0
        keylist[-1][2] = temp
        #keylist[-1][0] = 0.0

        length = len(keylist) - 2
        if length > 0:
            for i in range(length):
                i += 1
                keylist[i][0] = 1 - keylist[i][0] #invert keys
                keylist[i][1] = 1 - keylist[i][1] #invert values
                temp = keylist[i][2]
                keylist[i][2] = keylist[i][3] #swap tangents
                keylist[i][3] = temp
        return keylist

def GUI():
	spaceGUI()