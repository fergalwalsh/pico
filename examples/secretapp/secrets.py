import pico

def open_secret():
    return 42

@pico.protected
def top_secret():
    return "bla"

@pico.protected
def tell_secret(secret, pico_user):
    return "%s told us %s"%(pico_user, secret)

@pico.protected(users=['monty'], groups=['admins'])
def delete_secrets():
    #delete the secrets
    return "Everything is deleted. Not really."