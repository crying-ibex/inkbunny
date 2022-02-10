
# https://wiki.inkbunny.net/wiki/API

import json
from pathlib import Path
import os
import datetime
import getpass
from random import choices

import requests
from platformdirs import PlatformDirs # honestly get rid of this dependency


SUBMISSION_TYPES = {
    '1': 'Picture/Pinup',
    '2': 'Sketch',
    '3': 'Picture Series',
    '4': 'Comic',
    '5': 'Portfolio',
    '6': 'Shockwave/Flash - Animation',
    '7': 'Shockwave/Flash - Interactive',
    '8': 'Video - Feature Length',
    '9': 'Video - Animation/3D/CGI',
    '10': 'Music - Single Track',
    '11': 'Music - Album',
    '12': 'Writing - Document',
    '13': 'Character Sheet',
    '14': 'Photography - Fursuit/Sculpture/Jewelry/etc',
}


SIMPLE_SUBMISSION_TYPE_NUMBER = { # useful?
    'picture': '1',
    'pinup': '1',
    'pic': '1',
    'sketch': '2',
    'picture_series': '3',
    'series': '3',
    'comic': '4',
    'portfolio': '5',
    'flash_animation': '6',
    'flash': '6',
    'swf': '6',
    'flash_interactive': '7',
    'flash_game': '7',
    'interactive': '7',
    'game': '7',
    'feature_length_video': '8',
    'feature_length': '8',
    'video': '9',
    'vid': '9',
    'animation': '9',
    '3d_animation': '9',
    'anim': '9',
    'music_single': '10',
    'music': '10',
    'song': '10',
    'track': '10',
    'music_album': '11',
    'album': '11',
    'writing': '12',
    'document': '12',
    'story': '12',
    'doc': '12',
    'text': '12',
    'txt': '12',
    'character_sheet': '13',
    'reference_sheet': '13',
    'ref_sheet': '13',
    'char_sheet': '13',
    'photo': '14',
    'photograph': '14',
    'photography': '14',
    'fursuit': '14',
    'sculpture': '14',
    'jewelry': '14',
}


def ratings(ratingsmask):
    return {r: f"{ratingsmask: >5}"[idx] == '1'
        for idx, r in enumerate((
            'General',
            'Mature - Nudity',
            'Mature - Violence',
            'Adult - Sex',
            'Adult - Strong Violence'))}


class InkbunnyError(Exception):
    def __init__(self, error_code, error_message):
        self.error_code = error_code
        self.error_message = error_message

    def __str__(self):
        return self.error_message # todo


class Inkbunny():

    def __init__(self,
        username: str = None,
        password: str = None,
        sid: str = None,
        save_sid: bool = True,
        ):

        self.session_id_cache_directory = Path(
            PlatformDirs('inkbunnyapi', '').user_data_dir)

        self.s = requests.Session()
        self.s.hooks['response'].append(self._update_time)
        self.s.hooks['response'].append(self._handle_error)

        self.last_use_time = None

        self.sid = sid
        self.save_sid = save_sid
        self.username = username if username else 'guest'
        self.password = password

        self.login()


    def __enter__(self):
        return self


    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.logout()


    def _update_time(self, r, *args, **kwargs):
        self.last_use_time = (datetime.datetime.now().astimezone()
            - r.elapsed).isoformat()


    def _handle_error(self, r, *args, **kwargs):
        r.raise_for_status()

        response = r.json()
        if 'error_code' in response:
            raise InkbunnyError(
                response['error_code'], response['error_message'])


    def _save_session_id(self):
        data = {
            't': str(self.last_use_time),
            'sid': self.sid
        }
        sid_path = self.session_id_cache_directory / f'sid_{self.username}.json'
        sid_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sid_path, 'w') as sid_file:
            json.dump(data, sid_file)


    def _get_session_id(self, session_length_days: int = 2) -> str:
        if self.sid:
            # sid manually specified
            return self.sid

        # try reading from cache
        sid_path = self.session_id_cache_directory / f'sid_{self.username}.json'
        if sid_path.is_file():
            with open(sid_path) as sid_file:
                sid_data = json.load(sid_file)

            # I can't see anywhere where the valid duration of session ids are
            # listed, other than they "typically remain valid for several days
            # after their last use", so I'm using 2 days here by default.
            if ((datetime.datetime.now().astimezone()
                - datetime.datetime.fromisoformat(sid_data['t'])).days
                < session_length_days):

                self.sid = sid_data['sid']
                return self.sid

        # if can't use cache, log in again
        # check if guest first
        if self.username.lower() == 'guest':
            self.api_login('')

        elif self.password:
            self.api_login(self.password)

            self.password = None
            del self.password

        else:
            self.api_login(getpass.getpass(
                'Session ID not found or expired and password not supplied.'
                f'\nEnter password for {self.username}: '))

        if self.save_sid:
            self._save_session_id()

        return self.sid


    def api_login(self, password: str) -> dict:
        r = self.s.post('https://inkbunny.net/api_login.php', params={
                'username': self.username,
                'password': password})

        response = r.json()
        self.sid = response['sid']
        self.last_use_time = datetime.datetime.now().astimezone().isoformat()

        return response


    def api_logout(self) -> dict:
        r = self.s.post('https://inkbunny.net/api_logout.php',
            params={'sid': self.sid})

        return r.json()


    def login(self):
        self._get_session_id()
        self.s.params.update({'sid': self.sid})


    def logout(self):
        sid_path = self.session_id_cache_directory / f'sid_{self.username}.json'
        if sid_path.is_file():
            os.remove(sid_path)

        self.api_logout()


    def api_search(self, *,
        rid: str = None,
        submission_ids_only: bool = False,
        submissions_per_page: int = 30,
        page: int = 1,
        keywords_list: bool = False,
        no_submissions: bool = False,
        get_rid: bool = False,
        field_join_type: str = 'or',
        text: str = None,
        string_join_type: str = 'and',
        keywords: bool = True,
        title: bool = False,
        description: bool = False,
        md5: bool = False,
        keyword_id: int|str = None,
        username: str = None,
        user_id: int|str = None,
        favs_user_id: int|str = None,
        unread_submissions: bool = False,
        type_: list[int]|list[str]|set[int]|set[str]|tuple[int]|tuple[str]
            |int|str = None,
        sales: str = None,
        pool_id: int|str = None,
        orderby: str = 'create_datetime',
        dayslimit: int = None,
        random: bool = False,
        scraps: str = 'both',
        count_limit: int = 50000) -> list[dict]:

        arguments = locals()
        params = {}
        if text is not None and not any((keywords, title, description, md5)):
            # is ValueError the correct exception?
            raise UserWarning('At least one of \'keywords\', \'title\', '
                '\'description\', or \'md5\' must be True '
                'if text search is to work')

        if rid is not None:
            # if rid is specified, assume mode 2
            for (k, v) in list(arguments.items())[1:8]:
                if v != self.api_search.__kwdefaults__[k]:
                    if isinstance(v, bool):
                        params[k] = 'yes' if v else 'no'
                    else:
                        params[k] = v

        else:
            # mode 1 search
            if field_join_type not in ('or', 'and'):
                raise ValueError('field_join_type must be \'or\' or \'and\'')

            # 'exact' usage a little ambiguous in api documentation
            if string_join_type not in ('or', 'and', 'exact'):
                raise ValueError(
                    'string_join_type must be \'or\', \'and\', or \'exact\'')

            orderby_set = {'create_datetime', 'last_file_update_datetime',
                'unread_datetime', 'unread_datetime_reverse', 'views',
                'total_print_sales', 'total_digital_sales', 'total_sales',
                'username', 'fav_datetime', 'fav_stars', 'pool_order'}

            if orderby not in orderby_set:
                orderby_set_str = '    '.join(f"'{o}'\n" for o in orderby_set)
                raise ValueError('orderby must be one of:\n'
                    f'    {orderby_set_str}')

            if scraps not in ('both', 'no', 'only'):
                raise ValueError('scraps must be \'both\', \'no\', or \'only\'')

            if not 1 <= count_limit <= 50000:
                raise ValueError('count_limit must be between 1 and 50000')


            for (k, v) in list(arguments.items())[1:]:
                if v == self.api_search.__kwdefaults__[k]:
                    continue

                if isinstance(v, bool):
                    params[k] = 'yes' if v else 'no'

                elif k == 'type_' and v is not None:
                    if isinstance(type_, str|int):
                        type_ = {type_}

                    if all(str(t) for t in SUBMISSION_TYPES):
                        params['type'] = ','.join(set(type_))
                    else:
                        raise ValueError(
                            'Submission types (type_) must all be a numbers '
                            '(str or int type) between 1 and 15')

                else:
                    params[k] = v


        r = self.s.post('https://inkbunny.net/api_search.php', params=params)
        return r.json()


    def paginated_search(self, count: int, *,
        submission_ids_only: bool = False,
        keywords_list: bool = False,
        #
        field_join_type: str = 'or',
        text: str = None,
        string_join_type: str = 'and',
        keywords: bool = True,
        title: bool = False,
        description: bool = False,
        md5: bool = False,
        keyword_id: int|str = None,
        username: str = None,
        user_id: int|str = None,
        favs_user_id: int|str = None,
        type_: list[int]|list[str]|set[int]|set[str]|tuple[int]|tuple[str]
            |int|str = None, # special
        sales: str = None,
        pool_id: int|str = None,
        orderby: str = 'create_datetime',
        dayslimit: int = None,
        random: bool = False,
        scraps: str = 'both',
        ) -> list[dict]:

        arguments = locals()
        kwargs = {k: v for (k, v) in list(arguments.items())[2:]}
        if count <= 100:
            kwargs['submissions_per_page'] = count
            return self.api_search(**kwargs)['submissions']

        submissions = []
        kwargs['get_rid'] = 'yes'
        kwargs['submissions_per_page'] = 100
        first = self.api_search(**kwargs)
        total = int(first['results_count_all']) # api returns string (why?)
        rid = first['rid']
        submissions.extend(first['submissions'])

        if total <= 100:
            return submissions

        count = min(count, total)

        kwargs = {'rid': rid,
            'submission_ids_only': submission_ids_only,
            'keywords_list': keywords_list,
            'submissions_per_page': 100}

        for query_number in range(int(count/100)):
            page_number = 2 + query_number # already did page 1
            kwargs['page'] = page_number
            if page_number == int(count/100) + 1:
                kwargs['submissions_per_page'] = count % 100

            submissions.extend(self.api_search(**kwargs)['submissions'])

        return submissions


    def delete_submission(self, submission_id: str|int) -> dict:
        r = self.s.post('https://inkbunny.net/api_delsubmission.php',
            params={'submission_id': submission_id})

        return r.json()


    def delete_file_from_submission(self, file_id: str|int) -> dict:
        r = self.s.post('https://inkbunny.net/api_delfile.php',
            params={'file_id': file_id})

        return r.json()


    def submission_details(self,
        submission_ids: list[str]|list[int]|set[str]|set[int]|str|int, *,
        sort_keywords_by: str = 'alphabetical',
        show_description: bool = False,
        show_description_bbcode_parsed: bool = False,
        show_writing: bool = False,
        show_writing_bbcode_parsed: bool = False,
        show_pools: bool = False
        ) -> dict:

        arguments = locals()

        if isinstance(submission_ids, str|int):
            submission_ids = {submission_ids}

        if len(submission_ids) > 100:
            raise ValueError('Too many submission ids provided '
                f'({len(submission_ids)}). Maximum is 100.')

        params = {'submission_ids': ','.join(set(submission_ids))}

        if sort_keywords_by not in ('alphabetical', 'submissions_count'):
            raise ValueError('sort_keywords_by must be \'alphabetical\' '
                'or \'submissions_count\'')

        if sort_keywords_by == 'submissions_count':
            params['sort_keywords_by'] = 'submissions_count'

        for (k, v) in list(arguments.items())[3:]:
            if v:
                params[k] = 'yes'

        r = self.s.post(
            'https://inkbunny.net/api_submissions.php', params=params)

        response = r.json()
        return response['submissions']


    def md5_search(self, md5: str|list[str]|set[str]|tuple[str]) -> list[dict]:
        if isinstance(md5, str):
            md5 = {md5}

        query = ','.join(set(md5))

        if len(md5) > 100:
            return self.paginated_search(len(md5), text=query, md5=True)

        return self.api_search(text=query, md5=True)


    def submission_faving_users(self, submission_id: str) -> dict:
        r = self.s.post('https://inkbunny.net/api_submissionfavingusers.php',
            params={'submission_id': submission_id})

        return r.json()


    def unread_submissions(self, **kwargs) -> dict:
        return self.api_search(unread_submissions=True, **kwargs)


    def reorder_files(self, file_id: str|int, newpos: int) -> dict:
        r = self.s.post('https://inkbunny.net/api_reorderfile.php',
            params={'file_id': file_id, 'newpos': newpos})

        return r.json()


    def edit_submission_details(self, submission_id: int|str, *,
        title: str = None,
        desc: str = None,
        story: str = None,
        convert_html_entities: bool = False,
        type_: int|str = None, # special
        scraps: bool = None,
        use_twitter: bool = None,
        twitter_image_pref: int = None,
        visibility: str|bool = None,
        keywords: list[str] = None,
        nudity: bool = False, # tag[2]
        mild_violence: bool = False, # tag[3]
        sexual_themes: bool = False, # tag[4]
        strong_violence: bool = False, # tag[5]
        guest_block: bool = False,
        friends_only: bool = False
        ) -> dict:

        arguments = locals()

        rating_tags = {
            'nudity': 'tag[2]', 'mild_violence': 'tag[3]',
            'sexual_themes': 'tag[4]', 'strong_violence': 'tag[5]'}

        if str(type_) not in SUBMISSION_TYPES:

            if type_ in SIMPLE_SUBMISSION_TYPE_NUMBER:
                type_ = SIMPLE_SUBMISSION_TYPE_NUMBER[type_]

            else:
                raise ValueError('type_ must be a whole number '
                    '(int or str digits) between 1 and 15')

        if twitter_image_pref not in (None, 0, 1, 2):
            raise ValueError('If specified, twitter_image_pref must be 0, '
                '1, or 2')

        if visibility not in (None, 'yes', 'no', 'yes_nowatch', True, False):
            raise ValueError('If specified, visibility must either be bool, '
                'or str with value \'yes\', \'no\', or \'yes_nowatch\'')

        params = {'submission_id': submission_id}

        for (k, v) in list(arguments.items())[2:]:
            # allow for falsey things like empty strings
            if v is not None and v is not False:
                if k in rating_tags and v is True:
                    params[rating_tags[k]] = 'yes'
                elif v is True:
                    params[k] = 'yes'
                else:
                    params[k] = v


        r = self.s.post('https://inkbunny.net/api_editsubmission.php',
            params=params)

        return r.json()


    def watchlist(self, *,
        orderby: str = 'create_datetime',
        limit: int = None) -> list[dict]:

        if orderby not in ('alphabetical', 'create_datetime'):
            raise ValueError ('orderby must be either \'alphabetical\' '
                'or \'create_datetime\'')

        params = {}

        if orderby == 'alphabetical':
            params['orderby'] = 'alphabetical'

        if limit:
            params['limit'] = limit

        r = self.s.post('https://inkbunny.net/api_watchlist.php', params=params)
        return r.json()['watches']


    def _form_files(self,
        files: str|Path|list[str]|list[Path]|tuple[str]|tuple[Path],
        field: str) -> dict:

        files = ([Path(f) for f in files]
            if not isinstance(files, str|Path)
            else [Path(files)])

        if len(files) > 104: # where does this number come from?
            raise ValueError('Submissions may have at most 104 files, '
                f'{len(files)} given')

        if len(files) > 1 and any(f.suffix == '.zip' for f in files):
            raise ValueError('Only one .zip file may be uploaded at a time')

        if any(f.suffix == '.zip' and os.path.getsize(f) > 314572800
            for f in files):
            raise ValueError('.zip files may bot exceed 300MB in size')

        if any(os.path.getsize(f) > 104857600 and f.suffix != '.zip'
            for f in files):
            raise ValueError('Files may not exceed 100MB in size')

        if len(files) == 1:
            return {field: open(files[0], 'rb')}

        return {p.name: (field, open(p, 'rb')) for p in files}


    def _close_files(self, payload: dict):
        for v in payload.values():
            if isinstance(v, tuple):
                v[1].close()
            else:
                v.close()


    def upload(self,
        files: str|Path|list[str]|list[Path]|tuple[str]|tuple[Path] = None,
        submission_id: str|int = None, # when None given, new submission created
        progress_key: str = None, # recommend alpha-numeric string 32 chars long
        notify: bool = False,
        replace: str|int = None,
        thumbnail: str|Path = None,
        zipfile: str|Path = None,
        ) -> dict:

        payload = {}

        if files:
            payload |= self._form_files(files, 'uploadedfile[]')

        if thumbnail:
            payload |= self._form_files(thumbnail, 'uploadedthumbnail[]')

        if zipfile:
            payload |= self._form_files(zipfile, 'zipfile')

        params = {}
        if submission_id:
            params['submission_id'] = submission_id

        if replace:
            params['replace'] = replace

        if notify:
            params['notify'] = 'yes'

        if progress_key:
            params['progress_key'] = progress_key

        r = self.s.post('https://inkbunny.net/api_upload.php',
            params=params,
            files=payload,
            hooks={'response': lambda *a, **kw: self._close_files(payload)})

        return r.json()


    def _create_progress_key(self):
        return ''.join(choices(
            'abcdefghijklmnopqrstuvwxyz0123456789', k=32))


    def api_upload_progress(self, progress_key: str, cancel: bool = False):
        # this won't actually work in this wrapper, because the python requests
        # module is not asynchronous
        params = {'progress_key': progress_key}
        if cancel:
            params['cancel'] = 'yes'

        print('here-api_upload_progress')
        print(params)
        r = self.s.post('https://inkbunny.net/api_progress.php',
            params=params)

        return r.json()


    def new_submission(self, *,
        files: str|Path|list[str]|list[Path]|tuple[str]|tuple[Path] = None,
        progress_key: str = None,
        notify: bool = False,
        replace: str|int = None,
        thumbnail: str|Path = None,
        zipfile: str|Path = None,
        title: str = None,
        desc: str = None,
        story: str = None,
        convert_html_entities: bool = False,
        type_: int|str = None, # special
        scraps: bool = None,
        use_twitter: bool = None,
        twitter_image_pref: int = None,
        visibility: str|bool = None,
        keywords: list[str] = None,
        nudity: bool = False, # tag[2]
        mild_violence: bool = False, # tag[3]
        sexual_themes: bool = False, # tag[4]
        strong_violence: bool = False, # tag[5]
        guest_block: bool = False,
        friends_only: bool = False
        ) -> dict:

        arguments = locals()
        uploaded_submission = self.upload(
            **{k: v for (k, v) in list(arguments.items())[1:7]}
            )['submission_id']

        return self.edit_submission_details(uploaded_submission,
            **{k: v for (k, v) in list(arguments.items())[7:]})


    def search(self, query: str, results_count: int = 30, **kwargs):
        # todo
        return self.paginated_search(results_count, text=query, **kwargs)