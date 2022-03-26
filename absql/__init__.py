from inspect import cleandoc
from absql.files import parse
from absql.files.loader import generate_loader
from jinja2 import Template, DebugUndefined
from absql.macros import default_macros
from absql.text import clean_spacing, create_replacements, flatten_inputs
from absql.utils import nested_apply, get_function_arg_names, partialize_engine_func


class Runner:
    def __init__(self, extra_context={}, extra_constructors=[], **kwargs):
        self.extra_context = default_macros.copy()
        self.extra_context.update(extra_context)
        self.loader = generate_loader(extra_constructors)

    @staticmethod
    def render_text(text, replace_only=False, **vars):
        """
        Given some text, render the template with the vars.
        If a templated variable is unknown, leave it alone.
        """

        engine = vars.get("engine", None)
        for k, v in vars.items():
            if v.__class__.__name__ == "function":
                if "engine" in get_function_arg_names(v):
                    vars[k] = partialize_engine_func(v, engine=engine)

        if replace_only:
            text = clean_spacing(text)
            flat_vars = flatten_inputs(**vars)
            replacements = create_replacements(**flat_vars)
            for k, v in replacements.items():
                text = text.replace(k, str(v))
            return cleandoc(text)
        else:
            template = Template(text, undefined=DebugUndefined)
            return cleandoc(template.render(**vars))

    @staticmethod
    def render_file(
        file_path,
        extra_context={},
        extra_constructors=[],
        loader=None,
        replace_only=False,
    ):
        """
        Given a file, render SQL with the a combination of
        the vars in the file and any extras passed to extra_context.
        """
        if loader is None:
            loader = generate_loader(extra_constructors)

        file_contents = parse(file_path, loader=loader)

        sql = file_contents["sql"]
        file_contents.pop("sql")

        rendered_context = default_macros.copy()
        rendered_context.update(**extra_context)
        rendered_context.update(**file_contents)
        rendered_context = nested_apply(
            rendered_context,
            lambda x: Runner.render_text(x, replace_only, **rendered_context),
        )

        return Runner.render_text(sql, replace_only=replace_only, **rendered_context)

    def render(self, file_path, replace_only=False):
        """
        Given a file, render SQL with the a combination of
        the vars in the file and any extras passed to extra_context.
        """
        return self.render_file(
            file_path, self.extra_context, loader=self.loader, replace_only=replace_only
        )
