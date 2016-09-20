from globus_sdk.authorizers import BasicAuthorizer
from globus_sdk.auth.oauth2_constants import DEFAULT_REQUESTED_SCOPES
from globus_sdk.auth.client_types.base import AuthClient
from globus_sdk.auth.oauth2_authorization_code import (
    GlobusAuthorizationCodeFlowManager)
from globus_sdk.auth.token_response import OAuthDependentTokenResponse


class ConfidentialAppAuthClient(AuthClient):
    """
    This is a specialized type of ``AuthClient`` used to represent an App with
    a Client ID and Client Secret wishing to communicate with Globus Auth.
    It must be given a Client ID and a Client Secret, and furthermore, these
    will be used to establish a :class:`BasicAuthorizer
    <globus_sdk.authorizers.BasicAuthorizer` for authorization purposes.
    Additionally, the Client ID is stored for use in various calls.

    Confidential Applications (i.e. Applications with are not Native Apps) are
    those like the `Sample Data Portal
    <https://github.com/globus/globus-sample-data-portal>`_, which have their
    own credentials for authenticating against Globus Auth.

    Any keyword arguments given are passed through to the ``AuthClient``
    constructor.
    """
    # checked by BaseClient to see what authorizers are allowed for this client
    # subclass
    # only allow basic auth -- anything else means you're misusing the client
    allowed_authorizer_types = [BasicAuthorizer]

    def __init__(self, client_id, client_secret, **kwargs):
        if "authorizer" in kwargs:
            raise ValueError(
                "Cannot give a ConfidentialAppAuthClient an authorizer")

        AuthClient.__init__(
            self, client_id=client_id,
            authorizer=BasicAuthorizer(client_id, client_secret),
            **kwargs)

    def oauth2_client_credentials_token(self, requested_scopes=None):
        r"""
        Perform an OAuth2 Client Credentials Grant to get access tokens which
        directly represent your client and allow it to act on its own
        (independent of any user authorization).
        This method does not use a ``GlobusOAuthFlowManager`` because it is not
        at all necessary to do so.

        ``requested_scopes``
          A string of space-separated scope names being requested for the
          access token(s). Defaults to a set of commonly desired scopes for
          Globus.

        :rtype: :class:`OAuthTokenResponse
                <globus_sdk.auth.token_response.OAuthTokenResponse>`

        For example, with a Client ID of "CID1001" and a Client Secret of
        "RAND2002", you could use this grant type like so:

        >>> client = ConfidentialAppAuthClient("CID1001", "RAND2002")
        >>> tokens = client.oauth2_client_credentials_token()
        >>> transfer_token_info = (
        ...     tokens.by_resource_server["transfer.api.globus.org"])
        >>> transfer_token = transfer_token_info["access_token"]
        """
        requested_scopes = requested_scopes or DEFAULT_REQUESTED_SCOPES

        return self.oauth2_token({
            'grant_type': 'client_credentials',
            'scope': requested_scopes})

    def oauth2_start_flow_authorization_code(
            self, redirect_uri, requested_scopes=None,
            state='_default', refresh_tokens=False):
        """
        Starts an Authorization Code OAuth2 flow by instantiating a
        :class:`GlobusAuthorizationCodeFlowManager
        <globus_sdk.auth.GlobusAuthorizationCodeFlowManager>`

        All of the parameters to this method are passed to that class's
        initializer verbatim.
        """
        self.current_oauth2_flow_manager = GlobusAuthorizationCodeFlowManager(
            self, redirect_uri, requested_scopes=requested_scopes,
            state=state, refresh_tokens=refresh_tokens)
        return self.current_oauth2_flow_manager

    def oauth2_get_dependent_tokens(self, token):
        """
        Does a `Dependent Token Grant
        <https://docs.globus.org/api/auth/reference/#dependent_token_grant_post_v2_oauth2_token>`_
        against Globus Auth.
        This exchanges a token given to this client for a new set of tokens
        which give it access to resource servers on which it depends.
        This grant type is intended for use by Resource Servers playing out the
        following scenario:

          1. User has tokens for Service A, but Service A requires access to
             Service B on behalf of the user
          2. Service B should not see tokens scoped for Service A
          3. Service A therefore requests tokens scoped only for Service B,
             based on tokens which were originally scoped for Service A...

        In order to do this exchange, the tokens for Service A must have scopes
        which depend on scopes for Service B (the services' scopes must encode
        their relationship). As long as that is the case, Service A can use
        this Grant to get those "Dependent" or "Downstream" tokens for Service
        B.

        **Parameters**

            ``token`` (*string*)
              An Access Token as a raw string, being exchanged.

        :rtype: :class:`OAuthTokenResponse
                <globus_sdk.auth.token_response.OAuthTokenResponse>`
        """
        return self.oauth2_token({
            'grant_type': 'urn:globus:auth:grant_type:dependent_token',
            'token': token},
            response_class=OAuthDependentTokenResponse)

    def oauth2_token_introspect(self, token):
        """
        POST /v2/oauth2/token/introspect

        Get information about a Globus Auth token.

        >>> ac = globus_sdk.ConfidentialAppAuthClient(
        ...     CLIENT_ID, CLIENT_SECRET)
        >>> ac.oauth2_token_introspect('<token_string>')

        See
        `Token Introspection \
        <https://docs.globus.org/api/auth/reference/\
        #token_introspection_post_v2_oauth2_token_introspect>`_
        in the API documentation for details.
        """
        return self.post("/v2/oauth2/token/introspect",
                         text_body={'token': token})