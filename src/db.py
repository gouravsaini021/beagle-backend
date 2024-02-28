from databases import Database
import os
import json
from src import MYSQL_STRING

DB=Database(MYSQL_STRING)


async def initialize_tables(db: Database):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS Item (
            item_code VARCHAR(100) PRIMARY KEY,
            item_name VARCHAR(100),
            category VARCHAR(100),
            brand VARCHAR(255),
            barcode VARCHAR(255),
            MRP FLOAT,
            INDEX item_code (item_code)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS Store (
                    store_id VARCHAR(100) PRIMARY KEY ,
                    store_name VARCHAR(100),
                    address VARCHAR(255),
                    city VARCHAR(100),
                    state VARCHAR(100),
                    pincode VARCHAR(100),
                    country VARCHAR(100),
                    latitude DOUBLE,
                    longitude DOUBLE,
                    INDEX store_id (store_id)
                )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS Receipt (
            receipt_id INT AUTO_INCREMENT PRIMARY KEY,
            posting_date DATE,
            posting_time TIME,
            store_bill_no VARCHAR(100),
            receipt_store_name VARCHAR(100),
            gstin VARCHAR(100),
            address VARCHAR(255),
            total_amount FLOAT,
            store_id VARCHAR(100),
            store_name VARCHAR(255),
            text_from_image LONGTEXT,
            json_from_image LONGTEXT,
            FOREIGN KEY (store_id) REFERENCES Store(store_id) ON DELETE SET NULL
        );
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS ReceiptItems (
            name VARCHAR(10) PRIMARY KEY ,
            idx INT NOT NULL,
            bill_item_name VARCHAR(255) NOT NULL,
            item_code VARCHAR(100) ,
            item_name VARCHAR(255),
            price FLOAT,
            mrp FLOAT,
            qty FLOAT,
            amount Float,
            receipt_id INT,
            FOREIGN KEY (item_code) REFERENCES Item(item_code) ON DELETE SET NULL,
            FOREIGN KEY (receipt_id) REFERENCES Receipt(receipt_id) ON DELETE SET NULL
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS File (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            ip VARCHAR(100),
            receipt_id INT,
            file_name VARCHAR(100) NOT NULL,
            link VARCHAR(100) NOT NULL,
            folder VARCHAR(100) NOT NULL,
            sub_folder VARCHAR(100),
            FOREIGN KEY (receipt_id) REFERENCES Receipt(receipt_id) ON DELETE SET NULL
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS SoftUpload (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            ip VARCHAR(100),
            content_type VARCHAR(255),
            data LONGBLOB,
            unique_id VARCHAR(100),
            release_version VARCHAR(100),
            file_path VARCHAR(100),
            file_extension VARCHAR(10),
            file_link VARCHAR(100)
        )
    """)
