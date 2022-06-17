import os
import re
import json
import base64
import asyncio
import logging
import requests
import pyimgbox
import ptpimg_uploader

from rich import box
from rich.progress import track
from rich.console import Console

from ffmpy import FFmpeg
from pathlib import Path
from datetime import datetime
from imgurpython import ImgurClient

# For more control over rich terminal content, import and construct a Console object.
console = Console()


def _get_ss_range(duration, num_of_screenshots):
    # If no spoilers is enabled, then screenshots are taken from first half of the movie or tv show
    # otherwise screenshots are taken at regualar intervals from the whole movie or tv show
    no_spoilers = os.getenv("no_spoilers") or False
    first_time_stamp = (int(int(duration) / 2 ) if no_spoilers else int(duration)) / int(int(num_of_screenshots) + 1)

    list_of_ss_timestamps = []
    for num_screen in range(1, int(num_of_screenshots) + 1):
        millis = round(first_time_stamp) * num_screen
        list_of_ss_timestamps.append(str(datetime.strptime("%d:%d:%d" % (int((millis / (1000 * 60 * 60)) % 24), 
                int((millis / (1000 * 60)) % 60), int((millis / 1000) % 60)), '%H:%M:%S').time()))
    return list_of_ss_timestamps


def _upload_screens(img_host, img_host_api, image_path, torrent_title, base_path):
    # ptpimg does all for us to upload multiple images at the same time but to simplify things & 
    # allow for simple "backup hosts"/upload failures we instead upload 1 image at a time
    #
    # Both imgbb & freeimage are based on Chevereto which the API has us upload 1 image at a time while imgbox uses something custom 
    # and we upload a list of images at the same time
    #
    # Annoyingly pyimgbox requires every upload be apart of a "gallery", This is fine if you're uploading a list of multiple images at the same time
    # but because of the way we deal with "backup" image hosts/upload failures its not realistic to pass a list of all the images to imgbox at the same time.
    # so instead we just upload 1 image at a time to imgbox (also creates 1 gallery per image)
    #
    # Return values:
    # 1. Status
    # 2. BBCode|Medium|SizeLimit
    # 3. BBCode|Medium|NoSizeLimit
    # 4. BBCode|Thumbnail|NoSizeLimit
    # 5. Full Image URL
    #
    thumb_size = os.getenv("thumb_size") or "350"
    if img_host == 'imgur':
        try:
            client = ImgurClient(client_id=os.getenv('imgur_client_id'), client_secret=os.getenv('imgur_api_key'))
            response = client.upload_from_path(image_path)
            logging.debug(f'[Screenshots] Imgur image upload response: {response}')
            # return data
            return [
                True, 
                f'[url={response["link"]}][img={thumb_size}]{"m.".join(response["link"].rsplit(".", 1))}[/img][/url]', 
                f'[url={response["link"]}][img]{"m.".join(response["link"].rsplit(".", 1))}[/img][/url]',
                f'[url={response["link"]}][img]{"t.".join(response["link"].rsplit(".", 1))}[/img][/url]',
                response["link"]
            ]
        except Exception:
            logging.error(msg='[Screenshots] imgur upload failed, double check the ptpimg API Key & try again.')
            console.print("\imgur upload failed. double check the [bold]imgur_client_id[/bold] and in [bold]imgur_api_key[/bold] [bold]config.env[/bold]\n", style='Red', highlight=False)
            return False

    elif img_host == 'ptpimg':
        try:
            ptp_img_upload = ptpimg_uploader.upload(api_key=os.getenv('ptpimg_api_key'), files_or_urls=[image_path], timeout=5)
            # Make sure the response we get from ptpimg is a list
            assert type(ptp_img_upload) == list
            # assuming it is, we can then get the img url, format it into bbcode & return it
            logging.debug(f'[Screenshots] Ptpimg image upload response: {ptp_img_upload}')
            # TODO need to see the response and decide on the thumnail image and size
            # Pretty sure ptpimg doesn't compress/host multiple 'versions' of the same image so we use the direct image link for both parts of the bbcode (url & img)
            return [
                True, 
                f'[url={ptp_img_upload[0]}][img={thumb_size}]{ptp_img_upload[0]}[/img][/url]', 
                f'[url={ptp_img_upload[0]}][img]{ptp_img_upload[0]}[/img][/url]',
                f'[url={ptp_img_upload[0]}][img]{ptp_img_upload[0]}[/img][/url]', 
                ptp_img_upload[0]
            ]
        except AssertionError:
            logging.error(msg='[Screenshots] ptpimg uploaded an image but returned something unexpected (should be a list)')
            console.print(f"\nUnexpected response from ptpimg upload (should be a list). No image link found\n", style='Red', highlight=False)
            return False
        except Exception:
            logging.error(msg='[Screenshots] ptpimg upload failed, double check the ptpimg API Key & try again.')
            console.print(f"\nptpimg upload failed. double check the [bold]ptpimg_api_key[/bold] in [bold]config.env[/bold]\n", style='Red', highlight=False)
            return False
    
    elif img_host in ('imgbb', 'freeimage', 'imgfi', 'snappie'):
        # Get the correct image host url/json key
        available_image_host_urls = json.load(open(f'{base_path}/parameters/image_host_urls.json'))

        parent_key = 'data' if img_host == 'imgbb' else 'image'

        # Load the img_host_url, api key & img encoded in base64 into a dict called 'data' & post it
        image_host_url = available_image_host_urls[img_host]
        try:
            img_upload_request = None
            data = {'key': img_host_api}
            if img_host in ('imgfi', 'snappie'):
                files = {'source': open(image_path, 'rb')}
                img_upload_request = requests.post(url=image_host_url, data=data, files=files)
            else:
                data['image'] = base64.b64encode(open(image_path, "rb").read())
                img_upload_request = requests.post(url=image_host_url, data=data)
            
            if img_upload_request.ok:
                img_upload_response = img_upload_request.json()
                logging.debug(f'[Screenshots] Image upload response: {img_upload_response}')
                # When you upload an image you get a few links back, you get 'medium', 'thumbnail', 'url', 'url_viewer'
                try:
                    returnList = []
                    returnList.append(True) # setting the return status as true

                    if 'medium' in img_upload_response[parent_key]:
                        img_type = 'medium'
                        # if medium sized image is present then we'll use that as the second and thrid entry in the list.
                        # second one with thumbnail size limit and thrid without
                        returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img={thumb_size}]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                        returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                        if 'thumb' not in img_upload_response[parent_key]:
                            # thumbnail sized image is not present, hence we'll use medium sized image as fourth entry
                            returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')

                    if 'thumb' in img_upload_response[parent_key]:
                        img_type = 'thumb'
                        if len(returnList) == 3:
                            # if medium sized image was present, then the size of the list would be 3 
                            # hence we only need to add the 4th one as the thumbnail sized image without any size limits
                            returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                        else:
                            # no medium image type is present. hence we'll use thumb for those as well
                            # second will be the thumbnail sized image with size limit
                            # third and fourth will be thumbnail sized image wihtout any limits
                            returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img={thumb_size}]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                            returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                            returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                    
                    if len(returnList) != 4:
                        # neither of medium nor thumbnail sized image was present, so we'll just add the full image url as 2 3 and 4th entry
                        returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img={thumb_size}]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]')
                        returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key]["url"]}[/img][/url]')
                        returnList.append(f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key]["url"]}[/img][/url]')
                    
                    returnList.append(img_upload_response[parent_key]["url"])
                    return returnList
                except KeyError as key_error:
                    logging.error(f'[Screenshots] {img_host} json KeyError: {key_error}')
                    return False
            else:
                logging.error(f'[Screenshots] {img_host} upload failed. JSON Response: {img_upload_request.json()}')
                console.print(f"{img_host} upload failed. Status code: [bold]{img_upload_request.status_code}[/bold]", style='red3', highlight=False)
                return False
        except requests.exceptions.RequestException:
            logging.exception(f"[Screenshots] Failed to upload {image_path} to {img_host}")
            console.print(f"upload to [bold]{img_host}[/bold] has failed!", style="Red")
            return False
    
    # Instead of coding our own solution we'll use the awesome project https://github.com/plotski/pyimgbox to upload to imgbox
    elif img_host == "imgbox":
        async def imgbox_upload(filepaths):
            async with pyimgbox.Gallery(title=torrent_title, thumb_width=int(thumb_size)) as gallery:
                async for submission in gallery.add(filepaths):
                    logging.debug(f'[Screenshots] Imgbox image upload response: {submission}')
                    if not submission['success']:
                        logging.error(f"[Screenshots] {submission['filename']}: {submission['error']}")
                        return False
                    else:
                        logging.info(f'[Screenshots] imgbox edit url for {image_path}: {submission["edit_url"]}')
                        return [
                            True, 
                            f'[url={submission["web_url"]}][img={thumb_size}]{submission["image_url"]}[/img][/url]',
                            f'[url={submission["web_url"]}][img]{submission["image_url"]}[/img][/url]', 
                            f'[url={submission["web_url"]}][img]{submission["thumbnail_url"]}[/img][/url]',
                            submission["image_url"]
                        ]

        if os.path.getsize(image_path) >= 10485760:  # Bytes
            logging.error('[Screenshots] Screenshot size is over imgbox limit of 10MB, Trying another host (if available)')
            return False

        imgbox_asyncio_upload = asyncio.run(imgbox_upload(filepaths=[image_path]))
        if imgbox_asyncio_upload:
            return [
                True, 
                imgbox_asyncio_upload[1], 
                imgbox_asyncio_upload[2], 
                imgbox_asyncio_upload[3],
                imgbox_asyncio_upload[4]
            ]
    else:
        logging.fatal(f'[Screenshots] Invalid imagehost {img_host}. Cannot upload screenshots.')


def take_upload_screens(duration, upload_media_import, torrent_title_import, base_path, hash_prefix, discord_url, skip_screenshots=False):
    logging.basicConfig(filename=f'{base_path}/upload_script.log', level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    
    console.line(count=2)
    console.rule("Screenshots", style='red', align='center')
    console.line(count=1)

    num_of_screenshots = os.getenv("num_of_screenshots")

    logging.info(f"[Screenshots] Sanitizing the torrent title `{torrent_title_import}` since this is from TMDB")
    torrent_title_import = re.escape(torrent_title_import.replace(" ", '').replace("\\", '').replace("/", ''))
    logging.info(f"[Screenshots] Using {upload_media_import} to generate screenshots")
    logging.info(f'[Screenshots] Screenshots will be save with prefix {torrent_title_import}')
    console.print(f'\nTaking [chartreuse1]{str(num_of_screenshots)}[/chartreuse1] screenshots', style="Bold Blue")

    enabled_img_hosts_list = []
    if skip_screenshots:
        logging.info("[Screenshots] User has provided the `skip_screenshots` argument. Hence continuing without screenshots.")
        console.print('\nUser provided the argument `[red]skip_screenshots[/red]`. Overriding screenshot configurations in config.env', style='bold green')
    # ---------------------- check if 'num_of_screenshots=0' or not set ---------------------- #
    elif num_of_screenshots == "0" or not bool(num_of_screenshots):
        logging.error(f'[Screenshots] num_of_screenshots is {"not set" if not bool(num_of_screenshots) else f"set to {num_of_screenshots}"}, continuing without screenshots.')
        console.print(f'\nnum_of_screenshots is {"not set" if not bool(num_of_screenshots) else f"set to {num_of_screenshots}"}, \n', style='bold red')
    else:
        # ---------------------- verify at least 1 image-host is set/enabled ---------------------- #
        enabled_img_host_num_loop = 0
        while bool(os.getenv(f'img_host_{enabled_img_host_num_loop + 1}')):
            enabled_img_hosts_list.append(os.getenv(f'img_host_{enabled_img_host_num_loop + 1}'))
            enabled_img_host_num_loop += 1
        # now check if the loop ^^ found any enabled image hosts
        if not bool(enabled_img_host_num_loop):
            logging.error('[Screenshots] All image-hosts are disabled/not set (try setting "img_host_1=imgbox" in config.env)')
            console.print(f'\nNo image-hosts are enabled, maybe try setting [dodger_blue2][bold]img_host_1=imgbox[/bold][/dodger_blue2] in [dodger_blue2]config.env[/dodger_blue2]\n', style='bold red')

        # -------------------- verify an API key is set for 'enabled_img_hosts' -------------------- #
        for img_host_api_check in enabled_img_hosts_list:
            # Check if an API key is set for the image host
            if not bool(os.getenv(f'{img_host_api_check}_api_key')):
                logging.error(f"Can't upload to {img_host_api_check} without an API key")
                console.print(f"\nCan't upload to [bold]{img_host_api_check}[/bold] without an API key\n", style='red3', highlight=False)
                # If the api key is missing then remove the img_host from the 'enabled_img_hosts_list' list
                enabled_img_hosts_list.remove(img_host_api_check)
        # log the leftover enabled image hosts
        logging.info(f"[Screenshots] Image host order we will try & upload to: {enabled_img_hosts_list}")

    # -------------------------- Check if any img_hosts are still in the 'enabled_img_hosts_list' list -------------------------- #
    # if no image_hosts are left then we show the user an error that we will continue the upload with screenshots & return back to auto_upload.py
    # TODO: update this to work in line with the new json screenshot data
    if not bool(enabled_img_hosts_list):
        with open(f"{base_path}/temp_upload/{hash_prefix}bbcode_images.txt", "w") as no_images, open(f"{base_path}/temp_upload/{hash_prefix}url_images.txt", "a") as append_url_txt:
            no_images.write("[b][color=#FF0000][size=22]None[/size][/color][/b]")
            append_url_txt.write("No Screenshots Available")
            append_url_txt.close()
            no_images.close()
        logging.error(f"[Screenshots] Continuing upload without screenshots")
        console.print(f'Continuing without screenshots\n', style='chartreuse1')
        return

    # ##### Now that we've verified that at least 1 imghost is available & has an api key etc we can try & upload the screenshots ##### #
    # We only generate screenshots if a valid image host is enabled/available
    # Figure out where exactly to take screenshots by evenly dividing up the length of the video
    ss_timestamps_list = []
    screenshots_to_upload_list = []
    image_data_paths = []
    for ss_timestamp in track(_get_ss_range(duration=duration, num_of_screenshots=num_of_screenshots), description="Taking screenshots.."):
        # Save the ss_ts to the 'ss_timestamps_list' list
        ss_timestamps_list.append(ss_timestamp)
        screenshots_to_upload_list.append(f'{base_path}/temp_upload/{hash_prefix}screenshots/{torrent_title_import} - ({ss_timestamp.replace(":", ".")}).png')
        # Now with each of those timestamps we can take a screenshot and update the progress bar
        # `-itsoffset -2` added for Frame accurate screenshot
        if not Path(f'{base_path}/temp_upload/{hash_prefix}screenshots/{torrent_title_import} - ({ss_timestamp.replace(":", ".")}).png').is_file():
            FFmpeg(inputs={upload_media_import: f'-loglevel panic -ss {ss_timestamp} -itsoffset -2'}, 
                outputs={f'{base_path}/temp_upload/{hash_prefix}screenshots/{torrent_title_import} - ({ss_timestamp.replace(":", ".")}).png': '-frames:v 1 -q:v 10'}).run()
        else:
            logging.info(f"[Screenshots] Continuing upload existing screenshot: {torrent_title_import} - ({ss_timestamp.replace(':', '.')}).png")
        image_data_paths.append(f'{base_path}/temp_upload/{hash_prefix}screenshots/{torrent_title_import} - ({ss_timestamp.replace(":", ".")}).png')

    console.print('Finished taking screenshots!\n', style='sea_green3')
    # log the list of screenshot timestamps
    logging.info(f'[Screenshots] Taking screenshots at the following timestamps {ss_timestamps_list}')
    
    # checking whether we have previously uploaded all the screenshots. If we have, then no need to upload them again
    # if screenshots were not uploaded previously, then we'll upload them.
    # As of now partial uploads are not discounted for. During upload, all screenshots will be uploaded
    if Path(f'{base_path}/temp_upload/{hash_prefix}screenshots/uploads_complete.mark').is_file():
        logging.info("[Screenshots] Noticed that all screenshots have been uploaded to image hosts. Skipping Uploads")
        console.print('Reusing previously uploaded screenshot urls!\n', style='sea_green3')
    else:
        # ---------------------------------------------------------------------------------------- #
        # all different type of screenshots that the upload takes.
        images_data = { "bbcode_images" : "", "bbcode_images_nothumb" : "", "bbcode_thumb_nothumb" : "", "url_images" : "", "data_images": ""}

        for image_path in image_data_paths:
            images_data["data_images"] = f'{image_path}\n{images_data["data_images"]}'

        logging.info("[Screenshots] Starting to upload screenshots to image hosts.")
        console.print(f"Image host order: [chartreuse1]{' [bold blue]:arrow_right:[/bold blue] '.join(enabled_img_hosts_list)}[/chartreuse1]", style="Bold Blue")

        successfully_uploaded_image_count = 0

        for ss_to_upload in track(screenshots_to_upload_list, description="Uploading screenshots..."):
            # This is how we fall back to a second host if the first fails
            for img_host in enabled_img_hosts_list:
                # call the function that uploads the screenshot
                upload_image = _upload_screens(img_host=img_host, img_host_api=os.getenv(f'{img_host}_api_key'), image_path=ss_to_upload, torrent_title=torrent_title_import, base_path=base_path)
                # If the upload function returns True, we add it to bbcode_images.txt and url_images.txt
                if upload_image:
                    logging.debug(f"[Screenshots] Response from image host: {upload_image}")
                    images_data["bbcode_images"] = f'{upload_image[1]} {images_data["bbcode_images"]}'
                    images_data["bbcode_images_nothumb"] = f'{upload_image[2]} {images_data["bbcode_images_nothumb"]}'
                    images_data["bbcode_thumb_nothumb"] = f'{upload_image[3]} {images_data["bbcode_thumb_nothumb"]}'
                    images_data["url_images"] = f'{upload_image[4]}\n{images_data["url_images"]}'
                    successfully_uploaded_image_count += 1
                    # Since the image uploaded successfully, we need to break now so we don't reupload to the backup image host (if exists)
                    break

        logging.info('[Screenshots] Uploaded screenshots. Saving urls and bbcodes...')
        with open(f"{base_path}/temp_upload/{hash_prefix}screenshots/screenshots_data.json", "a") as screenshots_file:
            screenshots_file.write(json.dumps(images_data))

        # Depending on the image upload outcome we print a success or fail message showing the user what & how many images failed/succeeded
        if len(screenshots_to_upload_list) == successfully_uploaded_image_count:
            console.print(f'Uploaded {successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots', style='sea_green3', highlight=False)
            logging.info(f'[Screenshots] Successfully uploaded {successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots')
            # TODO persist this information in temp_upload and reuse during resume
            upload_marker = Path(f'{base_path}/temp_upload/{hash_prefix}screenshots/uploads_complete.mark')
            with upload_marker.open("w", encoding ="utf-8") as f:
                f.write("ALL_SCREENSHOT_UPLOADED_SUCCESSFULLY")
                logging.debug("[Screenshots] Marking that all screenshots have been uploaded successfully")
        else:
            console.print(f'{len(screenshots_to_upload_list) - successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots failed to upload', style='bold red', highlight=False)
            logging.error(f'[Screenshots] {len(screenshots_to_upload_list) - successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots failed to upload')
