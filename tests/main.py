from pprint import pprint

from aidbox.lib import Aidbox

ab = Aidbox(
    host='https://sansara.health-samurai.io',
    token='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJnaXZlbl9uYW1lIjpudWxsLCJiaXJ0aGRhdGUiOm51bGwsImVtYWlsIjoicGF0aWVudEBjb20uY29tIiwiem9uZWluZm8iOm51bGwsImxvY2FsZSI6bnVsbCwic3ViIjoicGF0aWVudCIsInBob25lIjpudWxsLCJuYW1lIjpudWxsLCJuaWNrbmFtZSI6bnVsbCwidXNlci1pZCI6InBhdGllbnQiLCJtaWRkbGVfbmFtZSI6bnVsbCwiZmFtaWx5X25hbWUiOm51bGwsInVwZGF0ZWRfYXQiOm51bGwsInBpY3R1cmUiOm51bGwsIndlYnNpdGUiOm51bGwsImdlbmRlciI6bnVsbCwicHJlZmVycmVkX3VzZXJuYW1lIjpudWxsLCJwcm9maWxlIjpudWxsfQ.ThigRLqfAc-xY9RHy75cI-Wh9s0y6dcRT_mSPRon4aOAsFL2BMkhGiLRjkDDRQa-e_BRDzSLgi84aB3q8atwTMSs9fYL79AzrNU3dgv9nyyjNy7BzRY_OYeTR3TBdEUklTnNABXiis0pS4JOw1JcDT0xpxtB2qBPpT7odPyVlHbjKWRINIqE2iAkTFOY_8UYCA-WU3qGEHDUdWFnav42aiDfcZNa2yBpytv7n8qqj70nCfXu49ShcT86eQ4vQsafNgfttRE1CbzqGVHS3Lv-nX25GSh_DJ_qITDC4Uk_KoMtGLzjW1LqvgRLWydEVbluj4SKlx1oYD07Yu6nCJcw2A')

# res = ab.resources('Entity').get('Patient')
res = ab.resources('Entity').search(
    type='resource',
    module='chat').all()

print('count', ab.resources('AccessToken').count())

x = ab.resources('Patient').search(name='John')
y= x.search(family='Steve')
print(x, y)


practitioner = ab.resource('Practitioner', id='new-pr')
practitioner.save()

patient = ab.resource('Patient', id='b38d148a-a474-4ae0-b0f9-5e8454bb7240',
                      general_practitioner=[practitioner],
                      name=[{'text': 'New Patient'}])
patient.save()
patient.delete()
practitioner.delete()




