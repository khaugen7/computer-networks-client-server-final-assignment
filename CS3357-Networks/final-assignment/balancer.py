import socket
import os
import datetime
import signal
import sys
import random

# Constant for our buffer size

BUFFER_SIZE = 1024

# Constant for our timeout

TIMEOUT = 300

# Constant for our performance test file

TEST_FILE = 'performanceTest.html'


# Signal handler for graceful exiting.

def signal_handler(sig, frame):
    print('Interrupt received, shutting down ...')
    sys.exit(0)


# A function for creating HTTP GET messages.

def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n'
    return request


# Read a file from the socket and print it out.  (For errors primarily.)

def print_file_from_socket(sock, bytes_to_read):

    bytes_read = 0
    while bytes_read < bytes_to_read:
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)
        print(chunk.decode())


# Read a file from the socket but do not save it.

def process_file_from_socket(sock, bytes_to_read):

    bytes_read = 0
    while bytes_read < bytes_to_read:
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)


# Create an HTTP response

def prepare_response_message(value):
    date = datetime.datetime.now()
    date_string = 'Date: ' + date.strftime('%a, %d %b %Y %H:%M:%S EDT')
    message = 'HTTP/1.1 '
    if value == '301':
        message = message + value + ' Moved Permanently\r\n' + date_string + '\r\n'
    elif value == '503':
        message = message + value + ' Service Unavailable\r\n' + date_string + '\r\n'

    return message


# Send the given response and file back to the client.

def send_response_to_client(sock, code, file_name, location):

    # Determine content type of file

    file_type = 'text/html'

    # Get size of file

    file_size = os.path.getsize(file_name)

    # Construct header and send it

    header = prepare_response_message(code) + 'Content-Type: ' + file_type + '\r\nContent-Length: ' + str(file_size) + '\r\nLocation: ' + location + '\r\n\r\n'
    sock.send(header.encode())

    # Open the file, read it, and send it

    with open(file_name, 'rb') as file_to_send:
        while True:
            chunk = file_to_send.read(BUFFER_SIZE)
            if chunk:
                sock.send(chunk)
            else:
                break


# Read a single line (ending with \n) from a socket and return it.
# We will strip out the \r and the \n in the process.

def get_line_from_socket(sock):

    done = False
    line = ''
    while not done:
        char = sock.recv(1).decode()
        if char == '\r':
            pass
        elif char == '\n':
            done = True
        else:
            line = line + char
    return line


# Function to initialize the array of servers based on the command line parameters entered by the user

def get_servers(argvs):
    servers = []
    for arg in argvs:
        try:
            server = arg.split(":")
            if len(server) != 2 or server[0] is None or server[1] is None:
                raise ValueError
            host = server[0]
            port = int(server[1])
            servers.append((host, port))
        except ValueError:
            print("Error: Invalid server format. Enter servers in the form: host:port")
            print("The provided server %s will not be added to the pool of servers" % arg)

    return servers


# Create a function to return the second value for each item in the ranked server array
# This is used to sort the servers according to their performance time

def sort_second(item):
    return item[1]


# Create our function to run a performance test on each server
# Returns the difference between the time when the transfer begins and when it ends
# Returns -1 on failure

def performance_test(server):
    host = server[0]
    port = server[1]
    print('Running performance test on the server at %s:%d ...' % (host, port))

    # On your mark, get set, GO!
    # Timer starts now

    start = datetime.datetime.now()

    # Attempt network connection for current server

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, port))
    except ConnectionRefusedError:
        print('Error:  That host or port is not accepting connections.')
        return -1
    except OSError:
        print('Error:  That host or port is not accepting connections.')
        return -1

    # The connection was successful, so we can prep and send our message.

    print('Connection to server established. Sending message...')
    message = prepare_get_message(host, port, TEST_FILE)
    server_socket.send(message.encode())

    # Receive the response from the server and start taking a look at it

    response_line = get_line_from_socket(server_socket)
    response_list = response_line.split(' ')
    headers_done = False

    # If an error is returned from the server, we print out the error details and
    # return -1 so the balancer knows to remove the server from it's pool of servers

    if response_list[1] != '200':
        print('Error:  An error response was received from the server.  Details:\n')
        print(response_line)
        bytes_to_read = 0
        while not headers_done:
            header_line = get_line_from_socket(server_socket)
            print(header_line)
            header_list = header_line.split(' ')
            if header_line == '':
                headers_done = True
            elif header_list[0] == 'Content-Length:':
                bytes_to_read = int(header_list[1])
        print_file_from_socket(server_socket, bytes_to_read)
        return -1

    # If it's OK, we retrieve and read the file to ensure the transfer is complete

    else:
        print('Success:  Server is sending test file.')

        # Go through headers and find the size of the file, then read it fully to confirm the transfer is complete

        bytes_to_read = 0
        while not headers_done:
            header_line = get_line_from_socket(server_socket)
            header_list = header_line.split(' ')
            if header_line == '':
                headers_done = True
            elif header_list[0] == 'Content-Length:':
                bytes_to_read = int(header_list[1])
        process_file_from_socket(server_socket, bytes_to_read)

        # Stop the clock and return the difference between start and end times

        end = datetime.datetime.now()
        print("File has been received and performance has been evaluated.\n")
        return end - start


# Function to take the performance evaluations of each server and return the server list ranked from
# fastest to slowest. It will also remove non-functioning servers from the server pool

def rank_servers(servers):
    ranked_servers = []
    for server in servers:
        time = performance_test(server)
        if time == -1:
            print('Removing server from server pool')
        else:
            ranked_servers.append((server, time))
    ranked_servers.sort(key=sort_second)
    for i in range(len(ranked_servers)):
        ranked_servers[i] = ranked_servers[i][0]
    return ranked_servers


# Function takes the ordered servers (from fastest to slowest) and returns a random server with faster
# servers being more likely to be chosen. This uses the same method suggested by the professor in the assignment
# outline (except with servers ordered from fastest to slowest instead of slowest to fastest)

def choose_server(servers):
    num_servers = len(servers)
    num_range = 0
    for i in range(1, num_servers + 1):
        num_range += i
    rand_int = random.randint(1, num_range)
    index = 1
    for i in range(num_servers):
        if rand_int in range(index, index + (num_servers - i)):
            return servers[i]
        index += num_servers - i


# Our main function.

def main():

    # Check if servers have been provided by the user

    if len(sys.argv) < 2:
        print("Load Balancer requires at least one server to be given as a command line parameter. Shutting down...")
        sys.exit(1)

    # Register our signal handler for shutting down.

    signal.signal(signal.SIGINT, signal_handler)

    # Initialize server array

    argvs = sys.argv[1:]
    servers = get_servers(argvs)

    # Do not allow balancer to be launched with zero servers configured (though there may be zero configured
    # after one of the performance tests down the line)

    if len(servers) == 0:
        print('No eligible servers provided. Shutting down...')
        exit(1)

    # Begin our loop to evaluate server performance when first launched and on socket timeout

    while True:

        # Sort servers according to performance test

        print("Running performance test on provided servers:\n")
        servers = rank_servers(servers)
        print("Performance test complete. Ready to accept client connections.\n")

        # Create the socket.  We will ask this to work on any interface and to pick
        # a free port at random.  We'll print this out for clients to use.

        balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        balancer_socket.settimeout(TIMEOUT)
        try:
            balancer_socket.bind(('', 0))
            print('Load balancer will wait for client connections at port ' + str(balancer_socket.getsockname()[1]))
            balancer_socket.listen(1)

            # Keep the server running forever.

            while True:
                print('Waiting for incoming client connection ...')
                conn, addr = balancer_socket.accept()
                print('Accepted connection from client address:', addr)
                print('Connection to client established, waiting to receive message...')

                # We obtain our request from the socket.  We only need to look at the filename, we can
                # leave the rest of the error handling up to the server(s)

                request = get_line_from_socket(conn)
                print('Received request:  ' + request)
                request_list = request.split()

                # The balancer doesn't care about headers, so we just clean them up.

                while get_line_from_socket(conn) != '':
                    pass

                # If requested file begins with a / we strip it off
                # We will need this for our redirection response header

                req_file = request_list[1]
                while req_file[0] == '/':
                    req_file = req_file[1:]

                # Return a 503 error if the server pool is empty

                if len(servers) == 0:
                    print('No server available! Responding with error!')
                    send_response_to_client(conn, '503', '503.html', 'NULL')

                else:
                    server = choose_server(servers)
                    location = 'http://%s:%d/%s' % (server[0], server[1], req_file)
                    print('Server available! Redirecting client to server now.')
                    send_response_to_client(conn, '301', '301.html', location)

                # We are all done with this client, so close the connection and
                # Go back to get another one!

                conn.close()

        except socket.timeout:
            print('\nSocket timed out, re-evaluating server performances...\n')


if __name__ == '__main__':
    main()
