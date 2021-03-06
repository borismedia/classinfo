# For Http calls
import httplib
import urllib
import json

# For system tools
import sys

# For reading passwords without echoing
import getpass


def main(argv=None):
    serverName,serverPort,token = inputTokenParams()
    if (token == None):
        return
    cluster = raw_input("Enter the cluster to move services to: ")
    
    # This request only needs the token and the response formatting parameter 
    params = urllib.urlencode({'token': token, 'f': 'json'})
    
    # Create site connection  
    httpConn = httplib.HTTPConnection(serverName, serverPort)
    folder = raw_input("Folder to move ('ROOT' for root folder, blank for entire site): ")
    if (folder == ""):
        changeClusterSite(httpConn,params,cluster)
    else:
        subfolders = str.upper(str(raw_input("Change cluster for subfolder? (Y/N) ")))[:1]
        while subfolders not in {"Y","N"}:
            subfolders = str.upper(str(raw_input("Y or N? ")))[:1]
        if subfolders == "Y":
            changeClusterSubfolders(httpConn,params,folder,cluster)
        else:
            changeClusterFolder(httpConn,params,folder,cluster)
            
def inputTokenParams():
    """Return tuple of serverName, serverPort,and token from raw_input parameters."""
    # Ask for admin/publisher user name and password
    username = raw_input("Enter user name: ")
    password = getpass.getpass("Enter password: ")
    
    # Ask for server name
    serverName = raw_input("Enter Server name: ")
    serverPort = 6080

    print "Obtaining token"

    # Get a token
    token = getToken(username, password, serverName, serverPort)
    if (token[2] == "" or token[2] == None):
        print "Could not generate a token with the username and password provided."
        token[2] == None
    else:
        print "Authenticated."
    return token

def getHttpHeaders():
    """Return the applicable http header used for all requests generated by this module."""
    return {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

def getFolderURL(folder="ROOT"):
    """Return the correct folder url given a folder name.
    
    Keyword arguments:
    folder -- the folder name (default "ROOT")

    """
    
    return "/arcgis/admin/services/" + getFolder(folder)

def getFolder(folder):
    """Return folder url in correct format given a folder name,
    
    Keyword arguments:
    folder -- the folder name (default "ROOT")

    """
    if (str.upper(str(folder)) == "ROOT" or str(folder) ==""):
        return ""
    else:
        return str(folder) + "/"
    

def changeClusterSite(httpConn,params,cluster="default"):
    """Change the cluster for all services in an ArcGIS Server site.

    Keyword arguments:
    httpConn -- An httplib.HTTPCOnnection connection to an ArcGIS Server machine
    params -- the urlencoded parameters to connect to the site
    cluster -- the cluster name to which the services are being moved (default "default")

    """
    changeClusterSubfolders(httpConn,params,"ROOT",cluster)

def changeClusterSubfolders(httpConn,params,folder,cluster="default"):
    """
    Change the cluster for all services in a given folder and all services in subfolders of that folder.

    Keyword arguments:
    httpConn -- An httplib.HTTPCOnnection connection to an ArcGIS Server machine
    params -- the urlencoded parameters to connect to the site
    folder -- the target folder
    cluster -- the cluster name to which the services are being moved (default "default")

    """
    changeClusterFolder(httpConn,params,folder,cluster)
    httpConn.request("POST",getFolderURL(folder),params,getHttpHeaders())
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "Could not read folder information."
        return
    else:
        data = response.read()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(data):          
            print "Error when reading folder information. " + str(data)
        else:
            print print "Folder properties read for folder " + str(folder) + "."

        # Deserialize response into Python object
        dataObj = json.loads(data)
        httpConn.close()

        #Loop through subfolder in the folder and change its cluster
        if dataObj.has_key('folders'):
            for item in dataObj['folders']:
                item = str(item)
                changeClusterSubfolders(httpConn,params,item,cluster)
        return

def changeClusterFolder(httpConn,params,folder,cluster="default"):
    """Change the cluster for all services in a given folder, but not subfolders.

    Keyword arguments:
    httpConn -- An httplib.HTTPCOnnection connection to an ArcGIS Server machine
    params -- the urlencoded parameters to connect to the site
    folder -- the target folder
    cluster -- the cluster name to which the services are being moved (default "default")

    """
    print "Changing cluster to '" + str(cluster) + "' for all services in folder " + str(folder) + "."
    httpConn.request("POST", getFolderURL(folder), params, getHttpHeaders())
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "Could not read folder information."
        return
    else:
        data = response.read()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(data):          
            print "Error when reading folder information. " + str(data)
        else:
            print print "Folder properties read for folder " + str(folder) + "."

        # Deserialize response into Python object
        dataObj = json.loads(data)
        httpConn.close()

        #Loop through each service in the folder and move its cluster
        for item in dataObj['services']:
            fullSvcName = item['serviceName'] + "." + item['type']
            changeCluster(httpConn, params, folder, fullSvcName, cluster)
        return
        
def changeCluster(httpConn,params,folder, service, cluster="default"):
    """Change the cluster for a given ArcGIS Server service.

    Keyword arguments:
    httpConn -- An httplib.HTTPCOnnection connection to an ArcGIS Server machine
    params -- the urlencoded parameters to connect to the site
    folder -- the folder in which the service resides
    service -- the full service name of the service as Name.type
    cluster -- the cluster name to which the services are being moved (default "default")

    """
    # Construct service URL, then get its current JSON definition
    serviceURL = "/arcgis/admin/services/" + getFolder(folder) + service
    httpConn.request("POST", serviceURL, params, getHttpHeaders())
    
    # Read response
    serviceResponse = httpConn.getresponse()
    if (serviceResponse.status != 200):
        httpConn.close()
        print "Error while reading service." + str(service) + "Please check the URL and try again."
        return
    else:
        serviceData = serviceResponse.read()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(serviceData):
            print "Error when reading service information. " + str(serviceData)                    
        else:
            print "\tService " + service + " read successfully. Changing cluster...."
    serviceObj = json.loads(serviceData)
    httpConn.close()

    # Change cluster of service
    if (serviceObj["clusterName"] != cluster):
        serviceObj["clusterName"] = cluster

        # Serialize back into JSON
        updatedSvcJson = json.dumps(serviceObj)

        # Call the edit operation on the service. Pass in modified JSON.
        editSvcURL = "/arcgis/admin/services/" + getFolder(folder) + service + "/edit"
        params = urllib.urlencode({'token': token, 'f': 'json', 'service': updatedSvcJson})
        httpConn.request("POST", editSvcURL, params, getHttpHeaders())
        
        # Read service edit response
        editResponse = httpConn.getresponse()
        if (editResponse.status != 200):
            httpConn.close()
            print "Error while executing edit."
            return
        else:
            editData = editResponse.read()
            
            # Check that data returned is not an error object
            if not assertJsonSuccess(editData):
                print "Error returned while editing service " + str(editData)        
            else:
                print "\tService edited successfully."
            httpConn.close()
    else:
        print "\tService already in cluster '" + cluster + "'."    
    return


def getToken(username, password, serverName, serverPort=6080,tokenURL="/arcgis/admin/generateToken"):
    """Return an ArcGIS Server token as (serverName,serverPort,token) given username, password and adminURL.

    Keyword arguemnts:
    username -- administrative login username
    password -- administrative login password, may be echoed in terminal
    serverName -- name of a server within the site
    serverPort -- server administrative communication port (default 6080)
    tokenURL -- the adminURL for token generation( default "/arcgis/admin/generateToken")

    """  
    params = urllib.urlencode({'username': username, 'password': password, 'client': 'requestip', 'f': 'json'})
    
    # Connect to URL and post parameters
    httpConn = httplib.HTTPConnection(serverName, serverPort)
    httpConn.request("POST", tokenURL, params, getHttpHeaders())
    
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "Error while fetching tokens from admin URL. Please check the URL and try again."
        return (serverName,serverPort,None)
    else:
        data = response.read()
        httpConn.close()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(data):            
            return (serverName,serverPort,None)
        
        # Extract the token from it
        token = json.loads(data)
        return (serverName,serverPort,token['token'])
        
def assertJsonSuccess(data):
    """Check that the input JSON object is not an error object."""
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        print "Error: JSON object returns an error. " + str(obj)
        return False
    else:
        return True
    
        
# Script start 
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
