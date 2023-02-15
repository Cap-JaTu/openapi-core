from typing import Any
from typing import Optional

from openapi_core.casting.schemas import schema_casters_factory
from openapi_core.casting.schemas.factories import SchemaCastersFactory
from openapi_core.deserializing.media_types import (
    media_type_deserializers_factory,
)
from openapi_core.deserializing.media_types.factories import (
    MediaTypeDeserializersFactory,
)
from openapi_core.deserializing.parameters import (
    parameter_deserializers_factory,
)
from openapi_core.deserializing.parameters.factories import (
    ParameterDeserializersFactory,
)
from openapi_core.protocols import BaseRequest
from openapi_core.protocols import Request
from openapi_core.protocols import WebhookRequest
from openapi_core.security import security_provider_factory
from openapi_core.security.factories import SecurityProviderFactory
from openapi_core.spec import Spec
from openapi_core.templating.paths.exceptions import PathError
from openapi_core.unmarshalling.request.datatypes import RequestUnmarshalResult
from openapi_core.unmarshalling.request.proxies import (
    SpecRequestValidatorProxy,
)
from openapi_core.unmarshalling.schemas import (
    oas30_write_schema_unmarshallers_factory,
)
from openapi_core.unmarshalling.schemas import (
    oas31_schema_unmarshallers_factory,
)
from openapi_core.unmarshalling.schemas.factories import (
    SchemaUnmarshallersFactory,
)
from openapi_core.unmarshalling.unmarshallers import BaseUnmarshaller
from openapi_core.util import chainiters
from openapi_core.validation.request.exceptions import MissingRequestBody
from openapi_core.validation.request.exceptions import ParametersError
from openapi_core.validation.request.exceptions import RequestBodyError
from openapi_core.validation.request.exceptions import SecurityError
from openapi_core.validation.request.validators import APICallRequestValidator
from openapi_core.validation.request.validators import BaseRequestValidator
from openapi_core.validation.request.validators import V30RequestBodyValidator
from openapi_core.validation.request.validators import (
    V30RequestParametersValidator,
)
from openapi_core.validation.request.validators import (
    V30RequestSecurityValidator,
)
from openapi_core.validation.request.validators import V30RequestValidator
from openapi_core.validation.request.validators import V31RequestBodyValidator
from openapi_core.validation.request.validators import (
    V31RequestParametersValidator,
)
from openapi_core.validation.request.validators import (
    V31RequestSecurityValidator,
)
from openapi_core.validation.request.validators import V31RequestValidator
from openapi_core.validation.request.validators import (
    V31WebhookRequestBodyValidator,
)
from openapi_core.validation.request.validators import (
    V31WebhookRequestParametersValidator,
)
from openapi_core.validation.request.validators import (
    V31WebhookRequestSecurityValidator,
)
from openapi_core.validation.request.validators import (
    V31WebhookRequestValidator,
)
from openapi_core.validation.request.validators import WebhookRequestValidator
from openapi_core.validation.schemas.factories import SchemaValidatorsFactory


class BaseRequestUnmarshaller(BaseRequestValidator, BaseUnmarshaller):
    def __init__(
        self,
        spec: Spec,
        base_url: Optional[str] = None,
        schema_casters_factory: SchemaCastersFactory = schema_casters_factory,
        parameter_deserializers_factory: ParameterDeserializersFactory = parameter_deserializers_factory,
        media_type_deserializers_factory: MediaTypeDeserializersFactory = media_type_deserializers_factory,
        schema_validators_factory: Optional[SchemaValidatorsFactory] = None,
        security_provider_factory: SecurityProviderFactory = security_provider_factory,
        schema_unmarshallers_factory: Optional[
            SchemaUnmarshallersFactory
        ] = None,
    ):
        BaseUnmarshaller.__init__(
            self,
            spec,
            base_url=base_url,
            schema_casters_factory=schema_casters_factory,
            parameter_deserializers_factory=parameter_deserializers_factory,
            media_type_deserializers_factory=media_type_deserializers_factory,
            schema_validators_factory=schema_validators_factory,
            schema_unmarshallers_factory=schema_unmarshallers_factory,
        )
        BaseRequestValidator.__init__(
            self,
            spec,
            base_url=base_url,
            schema_casters_factory=schema_casters_factory,
            parameter_deserializers_factory=parameter_deserializers_factory,
            media_type_deserializers_factory=media_type_deserializers_factory,
            schema_validators_factory=schema_validators_factory,
            security_provider_factory=security_provider_factory,
        )

    def _unmarshal(
        self, request: BaseRequest, operation: Spec, path: Spec
    ) -> RequestUnmarshalResult:
        try:
            security = self._get_security(request.parameters, operation)
        except SecurityError as exc:
            return RequestUnmarshalResult(errors=[exc])

        try:
            params = self._get_parameters(request.parameters, operation, path)
        except ParametersError as exc:
            params = exc.parameters
            params_errors = exc.errors
        else:
            params_errors = []

        try:
            body = self._get_body(request.body, request.mimetype, operation)
        except MissingRequestBody:
            body = None
            body_errors = []
        except RequestBodyError as exc:
            body = None
            body_errors = [exc]
        else:
            body_errors = []

        errors = list(chainiters(params_errors, body_errors))
        return RequestUnmarshalResult(
            errors=errors,
            body=body,
            parameters=params,
            security=security,
        )

    def _unmarshal_body(
        self, request: BaseRequest, operation: Spec, path: Spec
    ) -> RequestUnmarshalResult:
        try:
            body = self._get_body(request.body, request.mimetype, operation)
        except MissingRequestBody:
            body = None
            errors = []
        except RequestBodyError as exc:
            body = None
            errors = [exc]
        else:
            errors = []

        return RequestUnmarshalResult(
            errors=errors,
            body=body,
        )

    def _unmarshal_parameters(
        self, request: BaseRequest, operation: Spec, path: Spec
    ) -> RequestUnmarshalResult:
        try:
            params = self._get_parameters(request.parameters, path, operation)
        except ParametersError as exc:
            params = exc.parameters
            params_errors = exc.errors
        else:
            params_errors = []

        return RequestUnmarshalResult(
            errors=params_errors,
            parameters=params,
        )

    def _unmarshal_security(
        self, request: BaseRequest, operation: Spec, path: Spec
    ) -> RequestUnmarshalResult:
        try:
            security = self._get_security(request.parameters, operation)
        except SecurityError as exc:
            return RequestUnmarshalResult(errors=[exc])

        return RequestUnmarshalResult(
            errors=[],
            security=security,
        )


class BaseAPICallRequestUnmarshaller(BaseRequestUnmarshaller):
    pass


class BaseWebhookRequestUnmarshaller(BaseRequestUnmarshaller):
    pass


class APICallRequestUnmarshaller(
    APICallRequestValidator, BaseAPICallRequestUnmarshaller
):
    def unmarshal(self, request: Request) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal(request, operation, path)


class APICallRequestBodyUnmarshaller(
    APICallRequestValidator, BaseAPICallRequestUnmarshaller
):
    def unmarshal(self, request: Request) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal_body(request, operation, path)


class APICallRequestParametersUnmarshaller(
    APICallRequestValidator, BaseAPICallRequestUnmarshaller
):
    def unmarshal(self, request: Request) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal_parameters(request, operation, path)


class APICallRequestSecurityUnmarshaller(
    APICallRequestValidator, BaseAPICallRequestUnmarshaller
):
    def unmarshal(self, request: Request) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal_security(request, operation, path)


class WebhookRequestUnmarshaller(
    WebhookRequestValidator, BaseWebhookRequestUnmarshaller
):
    def unmarshal(self, request: WebhookRequest) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal(request, operation, path)


class WebhookRequestBodyUnmarshaller(
    WebhookRequestValidator, BaseWebhookRequestUnmarshaller
):
    def unmarshal(self, request: WebhookRequest) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal_body(request, operation, path)


class WebhookRequestParametersUnmarshaller(
    WebhookRequestValidator, BaseWebhookRequestUnmarshaller
):
    def unmarshal(self, request: WebhookRequest) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal_parameters(request, operation, path)


class WebhookRequestSecuritysUnmarshaller(
    WebhookRequestValidator, BaseWebhookRequestUnmarshaller
):
    def unmarshal(self, request: WebhookRequest) -> RequestUnmarshalResult:
        try:
            path, operation, _, path_result, _ = self._find_path(request)
        # don't process if operation errors
        except PathError as exc:
            return RequestUnmarshalResult(errors=[exc])

        request.parameters.path = (
            request.parameters.path or path_result.variables
        )

        return self._unmarshal_security(request, operation, path)


class V30RequestBodyUnmarshaller(
    V30RequestBodyValidator, APICallRequestBodyUnmarshaller
):
    schema_unmarshallers_factory = oas30_write_schema_unmarshallers_factory


class V30RequestParametersUnmarshaller(
    V30RequestParametersValidator, APICallRequestParametersUnmarshaller
):
    schema_unmarshallers_factory = oas30_write_schema_unmarshallers_factory


class V30RequestSecurityUnmarshaller(
    V30RequestSecurityValidator, APICallRequestSecurityUnmarshaller
):
    schema_unmarshallers_factory = oas30_write_schema_unmarshallers_factory


class V30RequestUnmarshaller(V30RequestValidator, APICallRequestUnmarshaller):
    schema_unmarshallers_factory = oas30_write_schema_unmarshallers_factory


class V31RequestBodyUnmarshaller(
    V31RequestBodyValidator, APICallRequestBodyUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31RequestParametersUnmarshaller(
    V31RequestParametersValidator, APICallRequestParametersUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31RequestSecurityUnmarshaller(
    V31RequestSecurityValidator, APICallRequestSecurityUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31RequestUnmarshaller(V31RequestValidator, APICallRequestUnmarshaller):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31WebhookRequestBodyUnmarshaller(
    V31WebhookRequestBodyValidator, WebhookRequestBodyUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31WebhookRequestParametersUnmarshaller(
    V31WebhookRequestParametersValidator, WebhookRequestParametersUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31WebhookRequestSecurityUnmarshaller(
    V31WebhookRequestSecurityValidator, WebhookRequestSecuritysUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


class V31WebhookRequestUnmarshaller(
    V31WebhookRequestValidator, WebhookRequestUnmarshaller
):
    schema_unmarshallers_factory = oas31_schema_unmarshallers_factory


# backward compatibility
class RequestValidator(SpecRequestValidatorProxy):
    def __init__(
        self,
        schema_unmarshallers_factory: "SchemaUnmarshallersFactory",
        **kwargs: Any,
    ):
        super().__init__(
            APICallRequestUnmarshaller,
            schema_validators_factory=(
                schema_unmarshallers_factory.schema_validators_factory
            ),
            schema_unmarshallers_factory=schema_unmarshallers_factory,
            **kwargs,
        )
