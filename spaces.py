import maya.cmds as cmds
import smartselection as sel

#contols:
    # new Space( time(FLOAT optional), selection(optional) - Create a new Space. Time = Time in which to look for a space, leaving blank will look at time sliders time. Selection = objects and attributes to work with in the format { object: { attribute:[]}}
    
    # version() - Output version name.
    
    # highlight() - Highlight keys that make up the Space
    
    # clear() - Delete all keys within the space.
    
    # scale( timescale(FLOAT optional), valuescale(FLOAT optional) ) - Scale Space by set values. Both variables scale based on value.
    
    # insert( keylist ) - Insert a keyset into the Space. Keylist = List of keys and values. [ frame, value, in, out ]
    
    # extract( shortlist(BOOL optional ) - Retrieves key data from selected spaces. Shortlist = Takes only the first Space found. Outputs a list omitting object and channel
    
    # inbetween( frames(INT optional) ) - Insert or remove an inbetween. Frames = number of frames to inbetween. Negative numbers remove frames

    # jump( frames(INT) ) - Jump forward or backward a frame from current position and output the time. Frames = number of frames to jump
#Space class for dealing with a space in the graph editor

class Space(object):
    
    #load up Space or check against selection if one is given
    def __init__(self, time = False, selection = False ):
        self._version = 'version 1.0 - jason.dixon.email@gmail.com'

            # ------- SELECTION ------- #
        self._selection = None #selection format { object : { attribute : [ left , right ] } }
        self._time = None #time somewhere in selected Space

        #if a time is given use that to find Spaces, otherwise use current time
        if time is False:
            self._time = cmds.currentTime(query = True)
        else:
            self._time = time
        
        selection = sel.smartSelection().get()
        #validate selection                    
        selection = self._validateSelection(selection)            
        if selection:
            #store the selection in class
            for obj in selection:
                for attr in selection[obj]:
                    borders = self._getSurroundingKeys(obj, attr)
                    if borders:
                        selection[obj][attr] = borders
            self._selection = selection
        else:
            print 'No Space Found.'
    #output version name
    def version(self):
        return self._version

    #validate selections are animateable, and have more than 1 key, and has a curve in range of time
    def _validateSelection(self, selection):
        if selection:
            validated = {}
            for obj in selection:
                valattr = {}
                for attr in selection[obj]:
                    if cmds.attributeQuery( attr, node= obj, ex=True): # w=True, k=True): #writable keyable exists
                        if cmds.keyframe( obj, attribute=attr, query=True, keyframeCount=True ) > 1: #more than one key
                            firstkey = cmds.findKeyframe( obj, attribute= attr, which='first')
                            lastkey = cmds.findKeyframe( obj, attribute= attr, which='last')
                            if firstkey <= self._time < lastkey: #is the curve within range of our time?
                                valattr[attr] = selection[obj][attr]
                if valattr:
                    validated[obj] = valattr
            if validated:
                return validated
        print 'Parts of the selection were not valid'
        return False

    #given frame number, check if the key at that frame is a breakdown or not
    def _checkBreakdown(self, time, object, channel):
        keycheck = cmds.keyframe( object, attribute = channel, bd = True , query = True, time = ( time , time ) )
        if keycheck:
            return True
        else:
            return False

    #check given time for key
    def _checkLocation(self, time, object, channel):
        keycheck = cmds.keyframe( object, attribute = channel, keyframeCount = True , query = True , time = ( time , time ) )
        if keycheck:
            return True
        else:
            return False    
    #grab the keys in front and behind the given time. Ignoring any breakdown keys
    def _getSurroundingKeys(self, object, channel):
        #are we on a key?
        if self._checkLocation( self._time, object, channel ) and not self._checkBreakdown( self._time, object, channel ):
            previouskey = self._time
        else:
            previouskey = self._findKey( object, channel, 'previous')
        nextkey = self._findKey( object, channel, 'next')
        #if both keys are the same, we are outside the time range.
        if nextkey == previouskey:
            return False
        else:
            return [previouskey , nextkey]

    #jump forward or backwards to find the previous non-breakdown key direction = "previous" or "next"
    def _findKey(self, object, channel, direction):
        #grab the last part of the string for "findkeyframe"
        failsafe = 10 #having this safety buffer means it will fail if there are more than 10 breakdown keys... hate infinite loops
        looking = True
        #time = 0.0
        time = self._time
        #loop through keys looking for next key
        while failsafe > 0 and looking:
            failsafe -= 1
            time = cmds.findKeyframe( object , attribute = channel , which = direction , time = (time,time) )
            #check returned key if it is a breakdown
            if not self._checkBreakdown(time, object, channel):
                #if we have a non-breakdown key return the frame number
                looking = False
        return time
    # ----- SELECTION ENDS ----- #
    
    # ---- HIGHLIGHT  SPACE ---- #
    def highlight(self):
        if self._selection:
            cmds.selectKey( clear = True )
            for obj in self._selection:
                for attr in self._selection[obj]:
                    cmds.selectKey( obj, at= attr, k=True, add=True, time=(self._selection[obj][attr][0],self._selection[obj][attr][1]) )
            return True 
        return False
        
    # ---- CLEAR OUT  SPACE ---- #
    def clear(self):      
        if self._selection:
            for obj in self._selection:
                for attr in self._selection[obj]:
                    cmds.cutKey( obj, attribute= attr, time= ( (self._selection[obj][attr][0] + 0.01) , (self._selection[obj][attr][1] - 0.01) ) ) 
            return True
        return False
        
    # ------ SCALE  SPACE ------ #
    #scale keys within provided range, pivoting from left side closest to zero
    def _scaleKeys(self, object, attr, range, timescale = 1, valuescale = 1):
        pivot = self._getKeyValue(range[0], object, attr)
        cmds.scaleKey( object, attribute = attr, t = (range[0],range[1]),vp = pivot[0], vs = valuescale) 
        cmds.scaleKey( object, attribute = attr, t = (range[0],range[1]),tp = range[0], ts = timescale)
    
    #get the value and tangent angle of a key given the time and channel
    def _getKeyValue(self, time, object, attr):
        value = cmds.keyframe( object, query = True, time = (time,time), valueChange = True, attribute = attr )
        angle = cmds.keyTangent( object, query = True, time = (time,time), attribute = attr, inAngle = True, outAngle = True)
        result = [ value[0] , angle[0] , angle[1] ]
        return result
    
    #scale the selection by a set value
    def scale(self, timescale = 1, valuescale = 1):
        if self._selection:
            for obj in self._selection:
                for attr in self._selection[obj]:
                    self._scaleKeys(obj, attr, self._selection[obj][attr], timescale, valuescale)
            return True
        return False
    # ---- SCALE SPACE ENDS ---- #
        
    # ---- INSERTING  CURVE ---- #
    #insert given key format = [ time , value , in angle , out angle ]
    def insert(self, keylist):
        cmds.undoInfo( openChunk = True)
        if self._selection and keylist:
            for obj in self._selection:
                for attr in self._selection[obj]:
                    #establish scale
                    uppervalue = self._getKeyValue( self._selection[obj][attr][1], obj, attr)
                    lowervalue = self._getKeyValue( self._selection[obj][attr][0], obj, attr)
                    shortval = uppervalue[0] - lowervalue [0]
                    shorttime = self._selection[obj][attr][1] - self._selection[obj][attr][0]
                    smallrange = [ self._selection[obj][attr][0] , (self._selection[obj][attr][0]+1) ] #key range when small
                    if uppervalue[0] == lowervalue[0]: #check we aren't dividing by zero
                        scalevalue = 1
                    else:
                        scalevalue = 1 / shortval
                    if self._selection[obj][attr][0] == self._selection[obj][attr][1]: # no divide by zero
                        scaletime = 1
                    else:
                        scaletime = 1 / shorttime
                    #scale keys down to 1 ratio
                    self._scaleKeys( obj, attr, self._selection[obj][attr], scaletime, scalevalue)
                    #set our borders
                    self._setBorder( obj, attr, smallrange, keylist[0][3], keylist[-1][2] )
                    #add keys
                    if len(keylist) > 2:
                        for i in range(len(keylist) - 2):
                            i += 1
                            keycopy = keylist[i][:] #copy list so we don't modify it
                            keycopy[0] += self._selection[obj][attr][0]
                            keycopy[1] += lowervalue[0]
                            self._createKey( obj, attr, keycopy )

                    #scale keys back to original size
                    self._scaleKeys(obj, attr, smallrange, shorttime, shortval)
            cmds.undoInfo( closeChunk = True)
            return True
        cmds.undoInfo( closeChunk = True)
        return False
        
    # ----- EXTRACT  CURVE ----- #
    def extract(self, shortlist = False): #shortlist generates keylist from first selection only
        cmds.undoInfo( stateWithoutFlush = False )
        if self._selection:
            objlist = {}
            for obj in self._selection:
                attrlist = {}
                for attr in self._selection[obj]:
                    #establish scale
                    uppervalue = self._getKeyValue( self._selection[obj][attr][1], obj, attr)
                    lowervalue = self._getKeyValue( self._selection[obj][attr][0], obj, attr)
                    shortval = uppervalue[0] - lowervalue [0]
                    shorttime = self._selection[obj][attr][1] - self._selection[obj][attr][0]
                    smallrange = [ self._selection[obj][attr][0] , (self._selection[obj][attr][0]+1) ] #key range when small
                    if uppervalue[0] == lowervalue[0]: #check we aren't dividing by zero
                        scalevalue = 1
                    else:
                        scalevalue = 1 / shortval
                    if self._selection[obj][attr][0] == self._selection[obj][attr][1]: # no divide by zero
                        scaletime = 1
                    else:
                        scaletime = 1 / shorttime
                    #scale keys down to 1 ratio
                    self._scaleKeys(obj, attr, self._selection[obj][attr], scaletime, scalevalue)
                    
                    #record keys
                    keylist = []
                    keys = cmds.keyframe( obj, attribute= attr, query = True, time= ( smallrange[0] , smallrange[1] ) )
                    for key in keys:
                        keydata = ( self._getKeyValue( key, obj, attr ) )
                        keydata.insert(0 , (key - smallrange[0]) )
                        keydata[1] -= lowervalue[0]
                        #keydata[2] = round(keydata[2],5) #round numbers a little
                        #keydata[3] = round(keydata[3],5)
                        keylist.append( keydata )
                    keylist[-1][1] = 1.0 #be sure that the end number is 1.0
                    #scale keys back to original size
                    self._scaleKeys(obj, attr, smallrange, shorttime, shortval)
                    if shortlist:
                        if keylist:
                            cmds.undoInfo( stateWithoutFlush = True )
                            return keylist
                        else:
                            cmds.undoInfo( stateWithoutFlush = True )
                            return False
                    if keylist:
                        attrlist[attr] = keylist
                if attrlist:
                    objlist[obj] = attrlist
            if objlist:
                cmds.undoInfo( stateWithoutFlush = True )
                return objlist
        cmds.undoInfo( stateWithoutFlush = True )
        return False
        
    # ------- IN BETWEEN ------- #
    def inbetween(self, frames = 1):
        cmds.undoInfo( openChunk = True)
        if self._selection:
            for obj in self._selection:
                for attr in self._selection[obj]:
                    movingkey = self._selection[obj][attr][1]
                    if movingkey == self._selection[obj][attr][0]:
                        diff = 0.0
                        scaletime = 1
                    else:
                        diff = movingkey - self._selection[obj][attr][0]
                        scaletime = 1 / diff
                    scaletime *= diff + frames
                    index = cmds.keyframe( obj, at = attr, q=True, iv=True, t=(movingkey,movingkey))
                    index = index[0]
                    if frames > ( diff*-1 ):
                        out = self._getKeyValue(movingkey,obj, attr) #grab out tangent
                        cmds.keyframe( obj, at= attr, t= (movingkey,999999), r= True, tc= frames )   
                        cmds.keyframe( obj, at= attr, index=(index,index), r= True, tc= (frames*-1) )   
                        self._scaleKeys( obj, attr, self._selection[obj][attr], scaletime )
                        cmds.keyTangent( obj, at=attr, index=(index,index), edit=True, oa = out[2] )
                    else:
                        cmds.undoInfo( closeChunk = True)
                        return False
            cmds.undoInfo( closeChunk = True)
            return True
        cmds.undoInfo( closeChunk = True)
        return False

    #set and break the tangents of the border keys borders = [frame , frame]
    def _setBorder(self, object, attr, borders, outangle, inangle):
        cmds.keyTangent( object , attribute = attr , time = (borders[0],borders[0]) , oa = outangle , lock = False , ow = 1)        
        cmds.keyTangent( object , attribute = attr , time = (borders[1],borders[1]) , ia = inangle , lock = False, iw = 1)
        
    #create a key at the given frame with a given value and angle etc
    def _createKey(self, object, attr, key):
        cmds.setKeyframe( object , attribute = attr , breakdown = True , value = key[1] , time = key[0] )
        cmds.keyTangent(  object , attribute = attr , time = (key[0],key[0]) , ia = key[2] , oa = key[3] , iw = 1 , ow = 1 )

    # ----- JUMP KEYFRAMES ----- #
    def jump(self, frames):
        if self._selection:
            old_time = self._time
            timelist = []
            if frames < 0:
                direction = 'previous'
                jump = frames * -1
            else:
                direction = 'next'
                jump = frames
            for obj in self._selection:
                for attr in self._selection[obj]:
                    for i in range(jump): #jump as many frames as requested
                        self._time = self._findKey(obj, attr, direction)
                    timelist.append(self._time)
                    self._time = old_time #reset time
            timelist.sort()
            if frames < 0:
                return timelist[-1]
            else:
                return timelist[0]
        return self._time
                        

    # ---- SPACE CLASS ENDS ---- #
