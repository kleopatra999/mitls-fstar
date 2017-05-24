import unittest



from ctypes import  CDLL, \
                    c_long, \
                    c_int, \
                    c_float, \
                    c_double, \
                    c_char_p, \
                    create_string_buffer, \
                    byref, \
                    c_voidp, \
                    c_int32,    \
                    c_uint8, \
                    c_uint32, \
                    CFUNCTYPE, \
                    POINTER    


SIZE_OF_METHODS 		= 288
SIZE_OF_VOID_P 	 		= 8
SIZE_OF_PRNET_ADDR      = 112

METHODS_NUM_POINTERS 	= int( SIZE_OF_METHODS / SIZE_OF_VOID_P )
METHODS_FILE_TYPE 		= 0 # see see nspr\pr\include\prio.h
METHODS_READ 			= 2
METHODS_WRITE           = 3
METHODS_GETPEERNAME     = 25
# METHODS_WRITEV          = 11

PR_DESC_FILE 		= 1
PR_DESC_SOCKET_TCP 	= 2
PR_DESC_SOCKET_UDP 	= 3
PR_DESC_LAYERED 	= 4
PR_DESC_PIPE 		= 5

PR_FAILURE          = -1
PR_SUCCESS          = 0

NULL_PTR = c_voidp( None )



class PRDLL():
    def __init__( self, nsprPath = "/home/user/dev/nss-3.30.2/nspr/Linux4.8_x86_64_cc_glibc_PTH_64_DBG.OBJ/pr/src/libnspr4.so" ):
        self.nspr   = CDLL( nsprPath )

        self.nspr.PR_AllocFileDesc.restype  = c_voidp
        self.nspr.PR_AllocFileDesc.argtypes = [ c_int, c_voidp ]  # see nspr\pr\include\private\pprio.h

        self.nspr.PR_FileDesc2NativeHandle.restype  = c_int
        self.nspr.PR_FileDesc2NativeHandle.argtypes = [ c_voidp ]

globalNSPR            = PRDLL()
globalDescriptorTable = {}

def ReadCallback( ctx, buffer, bufferSize ):
    print( "ReadCallback" )

    fileDescriptor = globalNSPR.nspr.PR_FileDesc2NativeHandle( c_voidp( ctx ) )
    print( "fileDescriptor = %s" % fileDescriptor )

    return globalDescriptorTable[ fileDescriptor ].ReadCallback( buffer, bufferSize )
    # pyBuffer = ( c_uint8 * bufferSize ).from_address( buffer )
    # for i in range( bufferSize ):
    #     pyBuffer[ i ] = c_uint8( i )

    # return bufferSize

def WriteCallback( ctx, buffer, bufferSize ):
    print( "ReadCallback" )

    fileDescriptor = globalNSPR.nspr.PR_FileDesc2NativeHandle( c_voidp( ctx ) )
    print( "fileDescriptor = %s" % fileDescriptor )

    return globalDescriptorTable[ fileDescriptor ].WriteCallback( buffer, bufferSize )

def GetPeernameCallback( fileDescriptor, addr ):
    print( "GetPeernameCallback" )
    addrBuffer = ( c_uint8 * SIZE_OF_PRNET_ADDR ).from_address( addr )

    for i in range( SIZE_OF_PRNET_ADDR ):
        addrBuffer[ i ] = 0

    return PR_SUCCESS

# def WritevCallback( a,b,c,d ):
#     print( "WritevCallback callback was called" )

#     return 42


# def NullCallback():
#     print( "Null callback was called" )

class PRWrapper():
    def __init__( self ):
        self.nspr   = globalNSPR.nspr
        
        self.cutils = CDLL( "cutils/cutils.so" )
        self.cutils.getAddress.restype = c_voidp

        self.ReadCallback   = None
        self.WriteCallback  = None

        self.SetupPRIOMethods()
        self.RegisterPRIOMethods()

    def SetupPRIOMethods( self ):
        READ_CALLBACK           = CFUNCTYPE( c_int, c_voidp, c_voidp, c_int ) 
        self.readCallback       = READ_CALLBACK( ReadCallback )

        WRITE_CALLBACK          = CFUNCTYPE( c_int, c_voidp, c_voidp, c_int ) 
        self.writeCallback      = WRITE_CALLBACK( WriteCallback )

        GET_PEERNAME_CALLBACK   = CFUNCTYPE( c_int, c_voidp, c_voidp )
        self.getPeernameCallback = GET_PEERNAME_CALLBACK( GetPeernameCallback )

        # NULL_CALLBACK       = CFUNCTYPE( None )
        # self.nullCallback   = NULL_CALLBACK( NullCallback )

        # WRITEV_CALLBACK       = CFUNCTYPE( c_int, c_voidp, c_voidp, c_int, c_int )
        # self.writevCallback   = WRITEV_CALLBACK( WritevCallback )

        self.PRIOMethods = (c_voidp * METHODS_NUM_POINTERS )()
        self.PRIOMethods[ METHODS_FILE_TYPE     ]   = PR_DESC_LAYERED
        self.PRIOMethods[ METHODS_READ          ]   = self.cutils.getAddress( self.readCallback )
        self.PRIOMethods[ METHODS_WRITE         ]   = self.cutils.getAddress( self.writeCallback )
        self.PRIOMethods[ METHODS_GETPEERNAME   ]   = self.cutils.getAddress( self.getPeernameCallback )
        # self.PRIOMethods[ METHODS_WRITEV ]      = self.cutils.getAddress( self.writevCallback )

    def RegisterPRIOMethods( self ):
        self.fileDescriptor = self.RegisterNewFileDescriptor()
        fakeFD              = c_int( self.fileDescriptor )

        self.prFileDesc = self.nspr.PR_AllocFileDesc( fakeFD, self.PRIOMethods )

    def RegisterNewFileDescriptor( self ):
        global globalDescriptorTable

        fileDescriptor = -1
        if len( globalDescriptorTable.keys() ) == 0:
            fileDescriptor = 1
        else:
            fileDescriptor = max( globalDescriptorTable.keys() ) + 1 

        globalDescriptorTable[ fileDescriptor ] = self

        return fileDescriptor

    def Read( self, size ):
        buffer  = bytearray( size )
        cBuffer = ( c_uint8 * size ).from_buffer( buffer )
        cSize   = c_int( size )

        ret = self.nspr.PR_Read( self.prFileDesc, cBuffer, cSize )
        print( "ret = %s, buffer = %s" % ( ret, buffer ) )

        return buffer

    def Write( self, buffer ):
        cBuffer = ( c_uint8 * len( buffer ) ).from_buffer( bytearray( buffer ) )
        cSize   = c_int( len( buffer ) )

        ret = self.nspr.PR_Write( self.prFileDesc, cBuffer, cSize )
        print( "ret = %s" % ( ret ) )

        return buffer

    def GetPeerName( self ):
        self.nspr.PR_GetPeerName.restype = c_int32

        prNetaddr = ( c_uint8 * SIZE_OF_PRNET_ADDR )()
        result = self.nspr.PR_GetPeerName( self.prFileDesc, prNetaddr )

        return ( result == PR_SUCCESS )

    # def WriteV( self ):
    #     # Used for testing NULL callback
    #     self.nspr.PR_Writev( NULL_PTR, NULL_PTR, c_int32( 0 ), c_int32( 0 ) )

class PRWrapperTester( unittest.TestCase ):
    def __init__(self, *args, **kwargs):
        super( PRWrapperTester, self).__init__(*args, **kwargs)

    def ReadCallbackForClient( self, buffer, bufferSize ):
        print( "ReadCallbackForClient" )
        pyBuffer = ( c_uint8 * bufferSize ).from_address( buffer )
        for i in range( bufferSize ):
            pyBuffer[ i ] = c_uint8( i )

        return bufferSize

    def ReadCallbackForServer( self, buffer, bufferSize ):
        print( "ReadCallbackForServer" )
        pyBuffer = ( c_uint8 * bufferSize ).from_address( buffer )
        for i in range( bufferSize ):
            pyBuffer[ i ] = c_uint8( i )

        return bufferSize

    def WriteCallbackForClient( self, buffer, bufferSize ):
        pyBuffer = ( c_uint8 * bufferSize ).from_address( buffer )
        print( "WriteCallbackForClient with buffer = %s" % bytearray( pyBuffer ) )

        return bufferSize

    def WriteCallbackForServer( self, buffer, bufferSize ):
        pyBuffer = ( c_uint8 * bufferSize ).from_address( buffer )
        print( "WriteCallbackForServer with buffer = %s" % bytearray( pyBuffer ) )
        
        return bufferSize

    def setUp(self):
        pass
        # self.prWrapper = PRWrapper()

    def tearDown(self):
        pass

    def testInitReadWrite( self ):
        clientSocket = PRWrapper()
        serverSocket = PRWrapper()

        clientSocket.ReadCallback = self.ReadCallbackForClient
        serverSocket.ReadCallback = self.ReadCallbackForServer
        clientSocket.WriteCallback = self.WriteCallbackForClient
        serverSocket.WriteCallback = self.WriteCallbackForServer

        clientSocket.Read( 10 )
        serverSocket.Read( 10 )

        clientSocket.Write( b"hello world!" )
        serverSocket.Write( b"hello world!" )

    def testGetPeerName( self ):
        socket = PRWrapper()

        self.assertTrue( socket.GetPeerName() )

    # def testNullCallback( self ):
    #     pr = PRWrapper()

    #     pr.WriteV()
        


if __name__ == '__main__':
	unittest.main()