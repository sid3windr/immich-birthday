# Immich Birthday Tooling

## Introduction

Together with many others, I discovered Immich as a very promising photo
collection app. With its facial recognition, it offers an option of setting
a person's birthdate, so it can show their age on every picture they feature in.

This script can create a CSV-formatted file with your recognized people, that
DO have a name assigned, are not hidden, and DO NOT have a birthday filled in.
You can fill in the CSV (manually or automated) and update the birthdays in Immich
to make full use of this nice "age" feature.

## Requirements

* Python 3
* An [Immich](https://immich.app) account
* An API key for your account

If you want to use CardDAV:
* A CardDAV server account (or API key)

## Creating an API key

* Click on your profile icon in the top right, then choose **Account Settings**.
* Fold out **API Keys** and click **New API Key**.
* Give it a useful name, like **immich-birthday**.
* Give it **person.read** and **person.update** permissions .
* Click **Create**. You'll be presented with a single chance to copy this API
key to your clipboard. Put it in your INI file (see below) and/or your
password manager.

## Configuration

### INI configuration

The scripts read `immich.ini` in the same directory as the script.

```
[immich]
url=https://immich.example.com
api_key=f9c899b3bef7fbe7c77729099c1463e5

[carddav]
url=https://app.monicahq.com/dav
username=hello@its.me
password=supersecret
;sleep=1
```

The `immich` section requires your Immich instance's URL, and the API key as
created above.

If you're not using CardDAV sync, you can ignore the `carddav` section.
Otherwise, see below.

### Environment variables

The scripts can also use environment variables instead of the INI file.
If the INI value is set, it will take precedence over the environment
variables.

Immich environment variable names are `IMMICH_URL` and `IMMICH_API_KEY`.

CardDAV environment variable names are `CARDDAV_URL`, `CARDDAV_USER`, `CARDDAV_PASS` and `CARDDAV_SLEEP`.

## Basic usage

### Fetching the birthday-less people

To create a CSV file with people without a birthday, run:

```
./birthdays.py --fetch --file birthdays.csv
```

You can now fill in the birthdays (YYYY-MM-DD format only) of the people you want to
have a birthday in Immich.

### Uploading the new birthdays

To upload your updated CSV file to Immich, run:

```
./birthdays.py --update --file birthdays.csv
```

It will only do correctly formatted dates, and please make sure the CSV
keeps its header line intact.

## CardDAV script

I have my own local instance of [Monica](https://www.monicahq.com) where I
keep contact details, including birthdays. Monica has a built in CardDAV
server which serves this information.

The `carddav.py` script ingests the CSV as created by `birthdays.py`, loops
through your CardDAV contacts, and outputs a CSV with filled out birthdays,
if the people were found on your CardDAV server. You can feed this CSV to
`birthdays.py` to update the birthdays in Immich.

It has optional `--input` and `--output` parameters for the input and output CSV
files (both in the same format). If you don't specify `--input`, stdin is
used; if you don't specify `--output`, stdout is used.

Please note I have only tested this against Monica's CardDAV implementation.

### CardDAV request speed throttling

The CardDAV client fetches each Vcard through a separate HTTP request.
Monica was not very happy and swiftly presented me with a "429 Too many requests"
error. I have implemented a `sleep` variable.

I have set my sleep value to 1, which sleeps for 1 second between every
requests. For default Monica rate limits, 0.5 was not slow enough. The
higher you set this, the longer the sync will take, as it will walk all
your CardDAV contacts in succession.

## Tying it all together

As both scripts tools by default use stdin and stdout... here's the magic
incantation:

```
./birthdays.py --fetch | ./carddav.py | ./birthdays.py --update
```

This will fetch all birthday-less people, dump them to stdout, which will be
fed in to the CardDAV client, which will look at your CardDAV server, and
output any found people with their birthday on stdout, which will be fed in
to the update script, which will tell Immich how old these people are. Throw
this in a cron job and enjoy automated updates!

## Future features

An enterprising person could implement a script similar to `carddav.py` which
syncs with Google Contacts, if that's where you keep your birthday information.
I myself am not planning to implement this, but I do welcome your contribution!

A `--silent` parameter may be useful for cron jobs.
