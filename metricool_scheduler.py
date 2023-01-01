import sys
import os
import pathlib
from PIL import Image
import piexif
from iptcinfo3 import IPTCInfo
from multiprocessing.pool import ThreadPool 

import PIL.ExifTags
import shutil
import tempfile
import pandas as pd
import datetime as dt
import boto3
import uuid

import google_drive_functions as g

def dir_builder(new_dir, wd):
    new_path = pathlib.Path(wd, new_dir)
    new_path.mkdir(parents=True, exist_ok=True)
    return(new_path)

def get_exif_fields(image, fields):
    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in image._getexif().items()
        if k in PIL.ExifTags.TAGS
    }
    fields = {field: exif[field] for field in fields}
    return(fields)

def create_uploader(image, p_to_upload, p_orig):
    # create exif data
    str_creator = u"Philip Massie IG:@philmassie"
    str_copywrite = u"All rights reserved"
    zeroth_ifd = {
        piexif.ImageIFD.Artist: str_creator,
        piexif.ImageIFD.Copyright: str_copywrite
        }
    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)

    # create blank image add exif
    data = list(image.getdata())
    image_without_exif = Image.new(image.mode, image.size)
    image_without_exif.putdata(data)

    # save to a temp file
    tmpf = tempfile.NamedTemporaryFile(delete=False, prefix="instgram_")
    image_without_exif.save(tmpf, exif=exif_bytes, format="JPEG", quality=100, subsampling=0)
    tmpf.close()
    tmpf.name

    # add IPTC data to tmpf and save final file
    info = IPTCInfo(tmpf.name)
    # add keyword
    info['by-line'] = ['Philip Massie IG:@philmassie']
    info['copyright notice'] = ['All rights reserved']

    # guid = str(uuid.uuid4())
    # dt_today = dt.datetime.now().date()
    # _p_to_upload = pathlib.Path(p_to_upload, f"{dt_today}_{guid}.jpg")
    dt_now = dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d-%H-%M-%S-%f')
    _p_to_upload = pathlib.Path(p_to_upload, f"{dt_now}.jpg")
    info.save_as(str(_p_to_upload))

    # delete tmp file
    os.unlink(tmpf.name)

    # Move original file to 'orig'
    os.rename(image.filename, pathlib.Path(p_orig, pathlib.Path(image.filename.split("\\")[-1])))

    return(_p_to_upload)

def uploader_aws(pl):
    client = boto3.client("s3")
    try:
        join_name = pl[1]
        path_to_upload = pl[0]
        file_name = str(path_to_upload).split('\\')[-1]
        path_uploaded = pl[2]
        bucket = "phils-metricool-stage"

        client.upload_file(str(path_to_upload), bucket, file_name)
        os.rename(path_to_upload, pathlib.Path(path_uploaded, file_name))
        return((join_name, f"https://{bucket}.s3.amazonaws.com/{file_name}"))

    except Exception as e:
        return(e)

def uploader_gdrive(pl):
    try:
        join_name = pl[1]
        path_to_upload = pl[0]
        file_name = pl[0].name
        path_uploaded = pl[2]
        service = pl[3]
        gdrive_folder_id = pl[4]

        # folder_info = g.create_folder("metricool_stage", service)

        # file_path = pathlib.Path("G:\\online_copies\\instagram\\2022\\staged\\uploaded\\7c5a2d9b-8c2f-41d3-8f74-c9b2dc82a2ed.jpg")
        # file_path = pathlib.Path("G:\\online_copies\\instagram\\2022\\staged\\uploaded\\08a64609-e96b-4a33-83d1-7580134c2ffb.jpg")

        file_info = g.upload_basic(path_to_upload, gdrive_folder_id, service)
        link = g.share_file(file_info[0]["id"], service)["webViewLink"]
        os.rename(path_to_upload, pathlib.Path(path_uploaded, file_name))
        return((join_name, link))

    except Exception as e:
        return(e)

def get_start_date():
    while True:
        try:
            dt_start = pd.to_datetime(input("First post date and time (YYYY-MM-DD HH:MM:SS)"))
            return(dt_start)
        except ValueError:
            continue
        else:
            break

# main function        
def main(sys_arg):
    try:
        # Make a list of all the files, paths and sortable names
        # test = pathlib.Path("G:\\online_copies\\instagram\\2022\\metricool\\staged")
        # test = pathlib.Path("G:\\online_copies\\instagram\\2022\\metricool\\staged\\test.txt")
        print("Building file list...")
        test = pathlib.Path(sys_arg[1])
        if test.is_dir():
            wd = test
            image_list = sorted([x for x in wd.iterdir() if x.is_file()])
        else:
            wd = test.parent
            image_list = sys_arg[1:]

        print(f"{len(image_list)} images to process.")

        print(f"WD:{wd}.")
        print("Collect some info.")
        # Choose which date and time to start posting

        dt_start = dt.datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        if dt_start.hour >= 19:
            dt_start = dt_start + dt.timedelta(days=1)
            
        while True:
            happy = input(f"Starting: {dt.datetime.strftime(dt_start, '%Y-%m-%d %H:%M:%S')}. Happy (Y/n)?") or "y"
            if happy.lower() != "y":
                dt_start = get_start_date()
                continue
            else:
                #we're happy with the value given.
                #we're ready to exit the loop.
                break

        # Create local folders
        dt_batch = dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d-%H-%M-%S')

        p_batch = dir_builder(f"batch_{str(dt_batch)}", wd)
        p_orig = dir_builder(f"orig", pathlib.Path(wd, p_batch))
        p_to_upload = dir_builder("to_upload", pathlib.Path(wd, p_batch))
        p_uploaded = dir_builder("uploaded", pathlib.Path(wd, p_batch))


        # Iterate over the images performing various steps
        post_data = []
        # image_path = image_list[0]
        for image_path in image_list:
            image = Image.open(image_path)

            image_data = {}

            # 1. file based info
            image_data["filename"]= pathlib.Path(image.filename)

            # 2. Grab the caption
            image_data["Text"] = get_exif_fields(image, ["ImageDescription"])["ImageDescription"]

            # 3. Create stripped down version for uploading
            image_data["to_upload"] = create_uploader(image, p_to_upload, p_orig)

            post_data.append(image_data)

        post_df = pd.DataFrame(post_data)

        # Now the uploads
        print("\nUploading")

        # AWS
        # ul_payload = list(zip(post_df["to_upload"], post_df["filename"], [p_uploaded]*len(post_df["filename"])))
        # pool = ThreadPool(processes=5)
        # result = pool.map(uploader_gdrive, ul_payload)

        # Google drive
        service = g.gauth()
        # get or create target folder
        parent = f"metricool_stage"
        folder_info = g.create_folder(parent, service)

        ul_payload = list(zip(
            post_df["to_upload"], post_df["filename"], 
            [p_uploaded]*len(post_df["filename"]), 
            [service]*len(post_df["filename"]), 
            [folder_info[0]["id"]]*len(post_df["filename"])
            ))

        result = []
        for f in ul_payload:
            result.append(uploader_gdrive(f))
        
        print("\tUploading complete")

        pdf_ul = pd.DataFrame(result, columns=["filename", "Picture Url 1"])

        # Finally build the dataframe for the csv
        col_order = ["Text", "Date", "Time", "Draft", "Facebook", "Twitter", "LinkedIn", "GMB", "Instagram", "Pinterest", "TikTok", "Youtube", "Picture Url 1", "Picture Url 2", "Picture Url 3", "Picture Url 4", "Picture Url 5", "Picture Url 6", "Picture Url 7", "Picture Url 8", "Picture Url 9", "Picture Url 10", "Shortener", "Pinterest Board", "Pinterest Pin Title", "Pinterest Pin Link", "Instagram Post Type", "Instagram Show Reel On Feed", "Youtube Video Title", "Youtube Video Type", "Youtube Video Privacy", "GMB Post Type", "Facebook Post Type", "Facebook Title"]

        start_date = dt.datetime.now().date()
        post_df["Date"] = [str(d.date()) for d in pd.date_range(dt_start, dt_start + dt.timedelta(days=len(post_df)-1))]
        post_df["Time"] = dt.datetime.strftime(dt_start, '%H:%M:%S')
        post_df["Instagram"] = "TRUE"
        post_df["Instagram Post Type"] = "POST"
        col_false = ["Draft", "Facebook", "Twitter", "LinkedIn", "GMB", "Pinterest", "TikTok", "Youtube", "Shortener"]
        for c in col_false:
            post_df[c] = "FALSE"

        col_blank = [c for c in col_order if c not in  post_df.columns]
        for c in col_blank:
            post_df[c] = ""

        post_df.columns
        post_df = post_df.drop(columns=['Picture Url 1'])
        post_df = post_df.merge(pdf_ul, on="filename", how="left")

        # Reorder
        post_df = post_df[col_order]

        post_df.to_csv(pathlib.Path(wd, f"metricool_{dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d-%H-%M-%S')}.csv"), index=False)

        # Now the uploads

    except Exception as ex:
        print(ex)
        input()

if __name__ == "__main__":
    # input("hello")
    # print(sys.argv)
    main(sys.argv)

