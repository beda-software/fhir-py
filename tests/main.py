from aidbox.lib import Aidbox

ab = Aidbox(
    host='https://sansara.health-samurai.io',
    email='patient@com.com',
    password='patient')

pr_res = ab.resource('Practitioner')

res = ab.resource('Patient')

res.generalPractitioner = pr_res

print(res.data)
