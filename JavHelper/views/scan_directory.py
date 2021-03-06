# -*- coding:utf-8 -*-
import os
import json
from ast import literal_eval
from flask import Blueprint, jsonify, request, Response

from JavHelper.core.OOF_downloader import OOFDownloader
from JavHelper.core import IniNotFoundException
from JavHelper.core.file_scanner import EmbyFileStructure
from JavHelper.core.ini_file import load_ini_file, return_config_string, set_value_ini_file, return_default_config_string

"""
This endpoint is pretty dangerous since it needs permission to r/w no-app directory
"""

directory_scan = Blueprint('directory_scan', __name__, url_prefix='/directory_scan')

@directory_scan.route('/rescan_emby_folder', methods=['GET'])
def rescan_emby_folder():
    """
    This endpoint is used to scan javs already exist locally and update db
    """
    emby_folder = EmbyFileStructure(return_default_config_string('file_path'))
    # scan folder
    emby_folder.scan_emby_root_path()

    return jsonify({'success': [jav_obj['directory'] for jav_obj in emby_folder.file_list]})

@directory_scan.route('/verify_local_nfo', methods=['GET'])
def verify_local_nfo():
    directory = request.args.get('directory')
    filename = request.args.get('filename')
    root = return_default_config_string('file_path')

    # special processing to convert linux db path to windows
    directory = directory.replace('/', os.sep).replace('\\', os.sep)

    print(os.path.join(root, directory, filename))
    whether_exists = os.path.isfile(os.path.join(root, directory, filename))
    return jsonify({'success': whether_exists})

@directory_scan.route('/update_oof_cookies', methods=['POST'])
def update_oof_cookies():
    req_data = json.loads(request.get_data() or '{}')
    update_dict = json.loads(req_data['update_dict'])

    status = OOFDownloader.update_local_cookies(update_dict)

    return jsonify({'status': status})

@directory_scan.route('/read_oof_cookies', methods=['GET'])
def read_oof_cookies():
    return jsonify({'oof_cookies': OOFDownloader.load_local_cookies(
        return_all=request.args.get('return_all', False)
    )})  # convert returned obj to dict format

@directory_scan.route('/update_local_ini', methods=['POST'])
def update_local_ini():
    req_data = json.loads(request.get_data() or '{}')
    update_dict = req_data['update_dict']

    status = set_value_ini_file(update_dict)

    return jsonify({'status': status})

@directory_scan.route('/read_local_ini', methods=['GET'])
def read_local_ini():
    if request.args.get('filter_dict'):
        res = {}
        errors = []
        filter_dict = literal_eval(request.args.get('filter_dict'))
        for k, v in filter_dict.items():
            try:
                res[k] = return_config_string(v)
            except IniNotFoundException as e:
                errors.append(str(e))
        return jsonify({'local_config': res, 'error': errors})
    else:
        return jsonify({'local_config': load_ini_file()._sections})  # convert returned obj to dict format


@directory_scan.route('/rename_path_preview', methods=['GET'])
def rename_path_preview():
    path = request.args.get('path')

    # handle usual error
    if not os.path.exists(path):
        return jsonify({'response': [{'file_name': f'{path} does not exist'}]}), 400
    if not os.path.isdir(path):
        return jsonify({'response': [{'file_name': f'{path} is not a valid directory for scan'}]}), 400

    res = EmbyFileStructure(path).rename_directory_preview()

    return jsonify({'response': res,
                    'header': [
                        {'name': 'Current File Name', 'selector': 'file_name', 'sortable': True},
                        {'name': 'New File Name', 'selector': 'new_file_name', 'sortable': True}
                    ]})


@directory_scan.route('/rename_path_on_json', methods=['POST'])
def rename_path_on_json():
    req_data = json.loads(request.get_data() or '{}')
    file_objs = req_data['file_objs']
    path = req_data['path']

    # handle usual error
    if not os.path.exists(path):
        return jsonify({'response': [{'file_name': f'{path} does not exist'}]}), 400
    if not os.path.isdir(path):
        return jsonify({'response': [{'file_name': f'{path} is not a valid directory for scan'}]}), 400

    def long_process():
        for each_file_process in EmbyFileStructure.rename_directory(path, file_objs):
            yield json.dumps({'log': each_file_process})+'\n'

    return Response(long_process(), mimetype='text/event-stream')


@directory_scan.route('/pre_scan_files', methods=['GET'])
def pre_scan_files():
    path = request.args.get('path')
    file_list = []

    # handle usual error
    if not os.path.exists(path):
        return jsonify({'response': [{'file_name': f'{path} does not exist'}]}), 400
    if not os.path.isdir(path):
        return jsonify({'response': [{'file_name': f'{path} is not a valid directory for scan'}]}), 400

    for file_name in os.listdir(path):
        # filter out dot file
        if file_name.startswith('.'):
            continue
        # don't care about directory size
        elif os.path.isdir(os.path.join(path, file_name)):
            #file_list.append({'file_name': file_name, 'size': 'folder - will not process'})
            # longer care about directory, just skip them
            pass
        else:
            file_size = os.path.getsize(os.path.join(path, file_name)) >> 20
            _car = os.path.splitext(file_name)[0]
            file_list.append({'file_name': file_name, 'car': _car, 'size': f'{file_size}MB'})

    return jsonify({'response': file_list,
                    'header': [
                        {'name': 'File Name', 'selector': 'file_name', 'sortable': True},
                        {'name': 'Size', 'selector': 'size', 'sortable': True}
                    ]
                    })
