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
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS ProcessedReceipt (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            modified datetime,
            softupload_id INT,
            is_processed VARCHAR(1),
            image_link VARCHAR(255),
            image_path VARCHAR(255),
            processed_text LONGTEXT,
            processed_json LONGTEXT,
            FOREIGN KEY (softupload_id) REFERENCES SoftUpload(id) ON DELETE SET NULL
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS Print2wa (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            timestamp datetime,
            ip VARCHAR(50),
            phone_number VARCHAR(50),
            device_id VARCHAR(100),
            release_version VARCHAR(100),
            file_link VARCHAR(100),
            file_extension VARCHAR(100),
            file_path VARCHAR(100),
            content_type VARCHAR(255)
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS TagSoftUpload (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            softupload_id INT,
            type VARCHAR(50) NOT NULL,
            sub_type VARCHAR(50),
            FOREIGN KEY (softupload_id) REFERENCES SoftUpload(id)
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS StoreProfile (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            store_name VARCHAR(255) NOT NULL,
            store_owner_name VARCHAR(255) NOT NULL,
            store_owner_contact_no VARCHAR(50) NOT NULL,
            store_landline_no VARCHAR(50),
            address text NOT NULL,
            locality VARCHAR(255),
            city VARCHAR(50) NOT NULL,
            state VARCHAR(50) NOT NULL,
            zipcode VARCHAR(50) NOT NULL,
            latitude VARCHAR(100) NOT NULL,
            longitude VARCHAR(100) NOT NULL,
            average_monthly_transaction int,
            average_monthly_turnover int,
            average_basket_sale_value int,
            store_format VARCHAR(10) NOT NULL,
            self_service VARCHAR(1) NOT NULL,
            presence_of_shopping_cart VARCHAR(1) NOT NULL,
            presence_of_shopping_basket VARCHAR(1) NOT NULL,
            store_profile VARCHAR(1) NOT NULL,
            no_of_tills int,
            business_hours VARCHAR(100),
            area_of_sqft INT NOT NULL,
            average_footfall INT NOT NULL,
            trade_profile_of_store VARCHAR(50),
            retail_percentage INT,
            presence_of_electronic_weighting_machine VARCHAR(1),
            presence_of_visi_cooler VARCHAR(1),
            presence_of_other_cooler VARCHAR(1),
            presence_of_freezer VARCHAR(1),
            air_cooling VARCHAR(1),
            pos_installation_date date,
            pos_make VARCHAR(100),
            pos_model VARCHAR(100),
            years_of_origin INT 
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS FMCG_Master (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            name VARCHAR(500),
            brand VARCHAR(50),
            manufacturer VARCHAR(50),
            mrp FLOAT,
            price FLOAT,
            discount_value FLOAT,
            discount_percentage FLOAT,
            category_lvl_1 VARCHAR(50),
            category_lvl_2 VARCHAR(50),
            category_lvl_3 VARCHAR(50),
            category_lvl_4 VARCHAR(50)
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS JioMart (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            modified datetime,
            product_code VARCHAR(100),
            name VARCHAR(500),
            brand VARCHAR(255),
            manufacturer VARCHAR(255),
            mrp FLOAT,
            price FLOAT,
            discount_value FLOAT,
            discount_percentage FLOAT,
            category_lvl_1 VARCHAR(255),
            category_lvl_2 VARCHAR(255),
            category_lvl_3 VARCHAR(255),
            category_lvl_4 VARCHAR(255)
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS ParsedItem (
        id INT AUTO_INCREMENT PRIMARY KEY,
        creation datetime,
        processed_receipt_id INT,
        observed_name VARCHAR(500),
        guessed_full_name VARCHAR(500),
        qty FLOAT,
        uom VARCHAR(50),
        mrp FLOAT,
        price FLOAT,
        total_amount FLOAT,
        barcode VARCHAR(255) DEFAULT NULL,
        date VARCHAR(50),
        time VARCHAR(50),
        store_name VARCHAR(255),
        store_address VARCHAR(255),
        bill_id VARCHAR(255),
        gstin VARCHAR(20),
        total_qty FLOAT,
        total_items FLOAT,
        final_amount FLOAT,
        store_cashier VARCHAR(255),
        store_phone_no VARCHAR(100),
        store_email VARCHAR(255),
        customer_phone_number VARCHAR(100),
        mode_of_payment VARCHAR(500),
        customer_name VARCHAR(500),
        customer_details VARCHAR(500),
        FOREIGN KEY (processed_receipt_id) REFERENCES ProcessedReceipt(id) ON DELETE SET NULL
)""")
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS bigbasket (
            id INT AUTO_INCREMENT PRIMARY KEY ,
            creation datetime,
            modified datetime,
            name VARCHAR(500),
            brand VARCHAR(255),
            mrp FLOAT,
            price FLOAT,
            ean_code VARCHAR(255),
            fssai_number VARCHAR(255),
            category_lvl_1 VARCHAR(255),
            category_lvl_2 VARCHAR(255),
            category_lvl_3 VARCHAR(255)
        )
    """)
    await db.execute(""" 
        CREATE TABLE IF NOT EXISTS MatchedItem (
        parsed_item_id INT PRIMARY KEY,
        creation DATETIME,
        jiomart_id INT,
        jiomart_matched VARCHAR(1),
        bigbasket_id INT,
        bigbasket_matched VARCHAR(1),
        FOREIGN KEY (parsed_item_id) REFERENCES ParsedItem(id),
        FOREIGN KEY (jiomart_id) REFERENCES JioMart(id) ON DELETE SET NULL,
        FOREIGN KEY (bigbasket_id) REFERENCES bigbasket(id) ON DELETE SET NULL   
)""")
    