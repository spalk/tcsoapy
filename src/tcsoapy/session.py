import datetime
from zeep import Client
from zeep.transports import Transport
from lxml import etree
from requests import Session


class TCSession:
    def __init__(self, url, username, password): 
        self.serveradress=url
        self.username=username
        self.password=password

        self.session_lifetime = datetime.timedelta(hours=1)
        self.session = None
        self.transport = None
        self.client = None
        self.raw_response = None

        self.__create_session()
            
    def __create_session(self):
        self.session = Session()
        self.__login()

    def __login(self):
        self.transport = Transport_decoration_free(session=self.session)
        self.client = self.__get_client()
        self.raw_response = self.client.service.login(username=self.username, password=self.password, group="", role="", sessionDiscriminator="1i52")

    def logout(self):
        self.client.service.logout()

    def get_transport(self):
        return self.transport

    def __get_client(self):
        service = 'Core-2006-03-Session'
        wsdl = self.__get_wsdl_url(self.serveradress, service)
        return Client(wsdl, transport=self.transport)

    @staticmethod
    def __get_wsdl_url(wsdl_host, wsdl_service):
        return '%s/%s?wsdl' % (wsdl_host, wsdl_service)


class Transport_decoration_free(Transport):
    def post_xml(self, address, envelope, headers):
        """Post the envelope xml element to the given address with the headers.
        In this modificaton `xml_declaration` is False to remove <?xml version='1.0' encoding='utf-8'?>
        For some reason server return empty page with status 200 with this line.
        """
        message = etree.tostring(envelope, pretty_print=False, xml_declaration=False, encoding="utf-8")
        return self.post(address, message, headers)