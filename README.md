# Project Setup Guide

Follow these steps to set up MySQL for your project and configure the necessary environment variable.

1. **Install MySQL:** Ensure that MySQL is installed on your system. Use the appropriate package manager based on your operating system. For example, on Ubuntu:

   ```bash
   sudo apt-get update
   sudo apt-get install mysql-server

2. Step 2: **Set MySQL Password:**Secure your MySQL installation by setting a password for the root user.feel free google entire process of install mysql and setup mysql password.
    ```bash
    sudo mysql_secure_installation

3. Step 3: **Configure Environment Variable**
    Edit the /etc/environment file to set the environment variable for your MySQL connection string.

    ```
    sudo vim /etc/environment
    ```

    Add the following line to the file, replacing placeholders with your actual values:

    ```
    MYSQL_STRING="mysql://user:password@localhost/database"
    ```
    change user,password and database variable from string and set actual values.
    Save and exit the editor.

    you might need to restart server if environement variable not reflect.
