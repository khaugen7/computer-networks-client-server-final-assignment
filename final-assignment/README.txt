Solution to CS3357 assignment 4, written by Kyle Haugen using some elements from
sample implementation of assignment 2.

server
------

To run an instance of the server, simply execute:

  python server.py

potentially substituting your installation of python3 in for python depending
on your distribution and configuration.  The server will report the port 
number that it is listening on for your client to use.  Place any files to 
transfer into the same directory as the server.

Make sure all html error files are in the same directory as the server(s). Server error files include:

   404.html 501.html 505.html

You will also need the following html file in the same directory as any server you have running for performance evaluation:

    performanceTest.html

client
------

To run the client, execute:

  python client.py http://host:port/file

where host is where the load balancer is running (e.g. localhost), port is the port
number reported by the load balancer where it is running and file is the name of the
file you want to retrieve.  Again, you might need to substitute python3 in for
python depending on your installation and configuration.

balancer
--------

To run the balancer, execute:

    python balancer.py host1:port1 host2:port2 ...

Where each host:port argument contains the host and port number of one of the server instances you have running.
You must have at least one server configured at launch or the program will terminate. Again, you might need to substitute python3 in for
python depending on your installation and configuration.

I made the decision to keep the program running in the case that no servers are remaining in the balancer server pool
after a performance evaluation so that any clients attempting to connect to the balancer will receive a 503 Service Unavailable
response instead of being unable to reach anything. However, the balancer will not launch if you fail to configure at least one
eligible server from the get-go.

Note: The port address for the balancer will change upon socket timeout (when it reruns the performance tests on the servers)
Be sure to update your client request with the new port number the next time you run it if it occurs after a timeout.

The balancer has a constant of five minutes configured as its timeout value at the top of the file.
Feel free to change this value for testing purposes.

The balancer requires the following error files to be stored in the same directory as the balancer itself:

    301.html 503.html
