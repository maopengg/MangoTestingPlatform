import com.sun.source.tree.AnnotationTree;
import com.sun.source.tree.AssignmentTree;
import com.sun.source.tree.BinaryTree;
import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.tree.LiteralTree;
import com.sun.source.tree.MemberSelectTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.ModifiersTree;
import com.sun.source.tree.NewArrayTree;
import com.sun.source.tree.NewClassTree;
import com.sun.source.tree.Tree;
import com.sun.source.tree.VariableTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.SourcePositions;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.Trees;

import javax.lang.model.element.Modifier;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;

/**
 * Dependency-free Spring MVC deterministic source indexer based on the public JDK Compiler Tree API.
 *
 * <p>The scanner intentionally calls {@link JavacTask#parse()} only. Spring Boot and Bean
 * Validation jars are therefore not required: unresolved annotation names remain available in
 * the parsed syntax tree. Every stdout line is one JSON event consumed by
 * {@code scan_springboot_ast.py}. Function bodies are not interpreted as business paths;
 * Human-readable fatal errors are written to stderr.</p>
 */
public final class SpringBootAstScanner {
    private static final String SCHEMA_VERSION = "3.0";
    private static final String TOOL_VERSION = "0.4.0";

    private static final Map<String, String> FIXED_MAPPING_METHODS;
    private static final Set<String> MAPPING_ANNOTATIONS;
    private static final Set<String> VALIDATION_ANNOTATIONS;
    private static final Map<String, String> REQUEST_BINDING_LOCATIONS;
    private static final Set<String> CONTROLLER_ANNOTATIONS;
    private static final Set<String> BUILTIN_TYPE_NAMES;

    static {
        Map<String, String> mappings = new LinkedHashMap<>();
        mappings.put("GetMapping", "GET");
        mappings.put("PostMapping", "POST");
        mappings.put("PutMapping", "PUT");
        mappings.put("PatchMapping", "PATCH");
        mappings.put("DeleteMapping", "DELETE");
        FIXED_MAPPING_METHODS = Collections.unmodifiableMap(mappings);

        Set<String> mappingNames = new LinkedHashSet<>(mappings.keySet());
        mappingNames.add("RequestMapping");
        MAPPING_ANNOTATIONS = Collections.unmodifiableSet(mappingNames);

        VALIDATION_ANNOTATIONS = Collections.unmodifiableSet(new LinkedHashSet<>(Arrays.asList(
                "NotNull", "NotBlank", "NotEmpty", "Null", "Size", "Min", "Max",
                "DecimalMin", "DecimalMax", "Pattern", "Positive", "PositiveOrZero",
                "Negative", "NegativeOrZero", "Digits", "Email", "Past", "PastOrPresent",
                "Future", "FutureOrPresent", "AssertTrue", "AssertFalse"
        )));

        Map<String, String> requestBindings = new LinkedHashMap<>();
        requestBindings.put("PathVariable", "path");
        requestBindings.put("RequestParam", "query");
        requestBindings.put("RequestHeader", "header");
        requestBindings.put("CookieValue", "cookie");
        requestBindings.put("RequestBody", "body");
        requestBindings.put("RequestPart", "part");
        requestBindings.put("ModelAttribute", "model");
        requestBindings.put("MatrixVariable", "matrix");
        requestBindings.put("RequestAttribute", "request_attribute");
        requestBindings.put("SessionAttribute", "session_attribute");
        REQUEST_BINDING_LOCATIONS = Collections.unmodifiableMap(requestBindings);

        CONTROLLER_ANNOTATIONS = Collections.unmodifiableSet(
                new LinkedHashSet<>(Arrays.asList("Controller", "RestController")));

        BUILTIN_TYPE_NAMES = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
                "String", "Boolean", "Byte", "Short", "Integer", "Long", "Float", "Double",
                "Character", "Object", "Void", "List", "Set", "Map", "Collection", "Iterable",
                "Optional", "Page", "Pageable", "ResponseEntity", "HttpServletRequest",
                "HttpServletResponse", "MultipartFile"
        )));
    }

    private SpringBootAstScanner() {
    }

    public static void main(String[] args) {
        try {
            Config config = Config.parse(args);
            int status = run(config);
            if (status != 0) {
                System.exit(status);
            }
        } catch (IllegalArgumentException exception) {
            System.err.println("SpringBootAstScanner: error: " + exception.getMessage());
            System.exit(2);
        } catch (Exception exception) {
            System.err.println("SpringBootAstScanner: fatal: " + exception.getClass().getSimpleName()
                    + ": " + String.valueOf(exception.getMessage()));
            exception.printStackTrace(System.err);
            System.exit(2);
        }
    }

    private static int run(Config config) throws IOException {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            System.err.println("SpringBootAstScanner: error: a full JDK is required; "
                    + "ToolProvider.getSystemJavaCompiler() returned null");
            return 2;
        }

        List<Path> files = readFileList(config.fileList);
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        State state = new State(config);

        try (StandardJavaFileManager fileManager = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            Iterable<? extends JavaFileObject> sources =
                    fileManager.getJavaFileObjectsFromPaths(files);
            List<String> options = Arrays.asList("-proc:none", "-Xlint:none", "-encoding", "UTF-8");
            JavacTask task = (JavacTask) compiler.getTask(
                    null, fileManager, diagnostics, options, null, sources);
            Iterable<? extends CompilationUnitTree> parsedUnits = task.parse();
            Trees trees = Trees.instance(task);
            SourcePositions positions = trees.getSourcePositions();

            List<CompilationUnitTree> units = new ArrayList<>();
            for (CompilationUnitTree unit : parsedUnits) {
                units.add(unit);
            }

            // Index source-defined Bean Validation constraints before endpoint
            // traversal so file order cannot change provenance decisions.
            for (CompilationUnitTree unit : units) {
                String relativePath = relativePath(config.root, unit.getSourceFile().toUri());
                SourceContext source = new SourceContext(relativePath, unit, positions);
                new CustomConstraintCollector(state, source).scan(unit, null);
            }
            boolean changed;
            do {
                changed = false;
                for (Map.Entry<String, Set<String>> entry : state.controllerMetaAnnotations.entrySet()) {
                    if (!Collections.disjoint(entry.getValue(), state.controllerStereotypes)) {
                        changed |= state.controllerStereotypes.add(entry.getKey());
                    }
                }
            } while (changed);

            for (CompilationUnitTree unit : units) {
                String relativePath = relativePath(config.root, unit.getSourceFile().toUri());
                SourceContext source = new SourceContext(relativePath, unit, positions);
                state.parsedFiles.add(relativePath);
                new UnitCollector(state, source).scan(unit, null);
            }
        }

        state.finishModelAndEnumEvidence();

        List<Map<String, Object>> diagnosticEvents = new ArrayList<>();
        for (Diagnostic<? extends JavaFileObject> diagnostic : diagnostics.getDiagnostics()) {
            Map<String, Object> item = linkedMap();
            item.put("kind", diagnostic.getKind().name());
            item.put("path", diagnostic.getSource() == null
                    ? null : relativePath(config.root, diagnostic.getSource().toUri()));
            item.put("line", positiveOrNull(diagnostic.getLineNumber()));
            item.put("column", positiveOrNull(diagnostic.getColumnNumber()));
            item.put("message", diagnostic.getMessage(Locale.ROOT));
            diagnosticEvents.add(item);
        }
        diagnosticEvents.sort(Comparator
                .comparing((Map<String, Object> item) -> String.valueOf(item.get("path")))
                .thenComparingLong(item -> numberValue(item.get("line")))
                .thenComparing(item -> String.valueOf(item.get("kind"))));

        state.endpoints.sort(Comparator
                .comparing((Endpoint endpoint) -> endpoint.method)
                .thenComparing(endpoint -> endpoint.path)
                .thenComparing(endpoint -> endpoint.relativePath)
                .thenComparing(endpoint -> endpoint.symbol));
        state.evidence.sort(Comparator
                .comparing((Evidence evidence) -> evidence.relativePath)
                .thenComparing(evidence -> evidence.symbol)
                .thenComparingLong(evidence -> evidence.line == null ? Long.MAX_VALUE : evidence.line)
                .thenComparing(evidence -> evidence.kind)
                .thenComparing(evidence -> evidence.evidenceId));

        for (Endpoint endpoint : state.endpoints) {
            emitEvent("endpoint", endpoint.toMap());
        }
        for (Evidence evidence : state.evidence) {
            emitEvent("evidence", evidence.toMap());
        }
        for (Map<String, Object> warning : state.warnings) {
            emitEvent("warning", warning);
        }
        for (Map<String, Object> diagnostic : diagnosticEvents) {
            emitEvent("diagnostic", diagnostic);
        }

        Map<String, Object> summary = linkedMap();
        summary.put("tool_version", TOOL_VERSION);
        summary.put("files_parsed", state.parsedFiles.size());
        summary.put("endpoint_count", state.endpoints.size());
        summary.put("evidence_count", state.evidence.size());
        summary.put("model_field_count", state.modelFields.size());
        summary.put("enum_count", state.enums.size());
        summary.put("warning_count", state.warnings.size());
        summary.put("diagnostic_count", diagnosticEvents.size());
        summary.put("diagnostic_error_count", diagnosticEvents.stream()
                .filter(item -> "ERROR".equals(item.get("kind"))).count());
        emitEvent("summary", summary);
        return 0;
    }

    private static List<Path> readFileList(Path fileList) throws IOException {
        List<Path> result = new ArrayList<>();
        for (String line : Files.readAllLines(fileList, StandardCharsets.UTF_8)) {
            String value = line.trim();
            if (!value.isEmpty()) {
                Path path = Paths.get(value).toAbsolutePath().normalize();
                if (!Files.isRegularFile(path)) {
                    throw new IllegalArgumentException("source file does not exist: " + path);
                }
                result.add(path);
            }
        }
        return result;
    }

    private static void emitEvent(String event, Object data) {
        Map<String, Object> record = linkedMap();
        record.put("event", event);
        record.put("data", data);
        System.out.println(Json.encode(record));
    }

    private static String relativePath(Path root, URI uri) {
        try {
            Path source = Paths.get(uri).toAbsolutePath().normalize();
            if (source.startsWith(root)) {
                return root.relativize(source).toString().replace('\\', '/');
            }
            return source.toString().replace('\\', '/');
        } catch (Exception ignored) {
            return uri.toString();
        }
    }

    private static Long positiveOrNull(long value) {
        return value > 0 ? value : null;
    }

    private static long numberValue(Object value) {
        return value instanceof Number ? ((Number) value).longValue() : Long.MAX_VALUE;
    }

    private static final class Config {
        final Path root;
        final Path fileList;
        final String routePrefix;

        private Config(Path root, Path fileList, String routePrefix) {
            this.root = root;
            this.fileList = fileList;
            this.routePrefix = routePrefix;
        }

        static Config parse(String[] args) {
            Path root = null;
            Path fileList = null;
            String routePrefix = null;
            for (int index = 0; index < args.length; index++) {
                String arg = args[index];
                if ("--root".equals(arg)) {
                    root = Paths.get(requireValue(args, ++index, arg)).toAbsolutePath().normalize();
                } else if ("--file-list".equals(arg)) {
                    fileList = Paths.get(requireValue(args, ++index, arg)).toAbsolutePath().normalize();
                } else if ("--route-prefix".equals(arg)) {
                    routePrefix = requireValue(args, ++index, arg);
                } else if ("--help".equals(arg) || "-h".equals(arg)) {
                    System.out.println("Usage: SpringBootAstScanner --root DIR --file-list FILE "
                            + "[--route-prefix /v3]");
                    System.exit(0);
                } else {
                    throw new IllegalArgumentException("unknown argument: " + arg);
                }
            }
            if (root == null) {
                throw new IllegalArgumentException("--root is required");
            }
            if (!Files.isDirectory(root)) {
                throw new IllegalArgumentException("--root is not a directory: " + root);
            }
            if (fileList == null || !Files.isRegularFile(fileList)) {
                throw new IllegalArgumentException("--file-list is required and must exist");
            }
            return new Config(root, fileList, routePrefix);
        }

        private static String requireValue(String[] args, int index, String option) {
            if (index >= args.length) {
                throw new IllegalArgumentException(option + " requires a value");
            }
            return args[index];
        }
    }

    private static final class SourceContext {
        final String relativePath;
        final CompilationUnitTree unit;
        final SourcePositions positions;
        final String packageName;

        SourceContext(String relativePath, CompilationUnitTree unit, SourcePositions positions) {
            this.relativePath = relativePath;
            this.unit = unit;
            this.positions = positions;
            this.packageName = unit.getPackageName() == null ? "" : unit.getPackageName().toString();
        }

        Long line(Tree tree) {
            long position = positions.getStartPosition(unit, tree);
            if (position == Diagnostic.NOPOS || unit.getLineMap() == null) {
                return null;
            }
            return positiveOrNull(unit.getLineMap().getLineNumber(position));
        }

        Long endLine(Tree tree) {
            long position = positions.getEndPosition(unit, tree);
            if (position == Diagnostic.NOPOS || unit.getLineMap() == null) {
                return line(tree);
            }
            return positiveOrNull(unit.getLineMap().getLineNumber(Math.max(0, position - 1)));
        }

        boolean hasAnnotationSource(AnnotationTree annotation, String... packageNames) {
            String annotationType = annotation.getAnnotationType().toString();
            String name = simpleName(annotationType);
            if (annotationType.contains(".")) {
                for (String packageName : packageNames) {
                    if (annotationType.equals(packageName + "." + name)) {
                        return true;
                    }
                }
                return false;
            }

            Set<String> explicitImports = new LinkedHashSet<>();
            for (ImportTree importTree : unit.getImports()) {
                if (importTree.isStatic()) {
                    continue;
                }
                String imported = importTree.getQualifiedIdentifier().toString();
                if (!imported.endsWith(".*") && imported.endsWith("." + name)) {
                    explicitImports.add(imported);
                }
            }
            if (!explicitImports.isEmpty()) {
                if (explicitImports.size() != 1) {
                    return false;
                }
                String imported = explicitImports.iterator().next();
                for (String packageName : packageNames) {
                    if (imported.equals(packageName + "." + name)) {
                        return true;
                    }
                }
                return false;
            }

            for (String packageName : packageNames) {
                if (packageName.equals(this.packageName)) {
                    return true;
                }
            }
            for (ImportTree importTree : unit.getImports()) {
                if (importTree.isStatic()) {
                    continue;
                }
                String imported = importTree.getQualifiedIdentifier().toString();
                for (String packageName : packageNames) {
                    if (imported.equals(packageName + ".*")) {
                        return true;
                    }
                }
            }
            return false;
        }

        Set<String> annotationQualifiedCandidates(AnnotationTree annotation) {
            String annotationType = annotation.getAnnotationType().toString();
            String name = simpleName(annotationType);
            Set<String> candidates = new LinkedHashSet<>();
            if (annotationType.contains(".")) {
                candidates.add(annotationType);
                if (!packageName.isEmpty()
                        && Character.isUpperCase(annotationType.charAt(0))) {
                    candidates.add(packageName + "." + annotationType);
                }
                return candidates;
            }

            Set<String> explicitImports = new LinkedHashSet<>();
            for (ImportTree importTree : unit.getImports()) {
                if (importTree.isStatic()) {
                    continue;
                }
                String imported = importTree.getQualifiedIdentifier().toString();
                if (!imported.endsWith(".*") && imported.endsWith("." + name)) {
                    explicitImports.add(imported);
                }
            }
            if (!explicitImports.isEmpty()) {
                candidates.addAll(explicitImports);
                return candidates;
            }
            candidates.add(packageName.isEmpty() ? name : packageName + "." + name);
            for (ImportTree importTree : unit.getImports()) {
                if (importTree.isStatic()) {
                    continue;
                }
                String imported = importTree.getQualifiedIdentifier().toString();
                if (imported.endsWith(".*")) {
                    candidates.add(imported.substring(0, imported.length() - 2) + "." + name);
                }
            }
            return candidates;
        }
    }

    private static final class RouteContext {
        final List<RouteVariant> variants;

        RouteContext(List<RouteVariant> variants) {
            this.variants = variants;
        }

        static RouteContext root() {
            return new RouteContext(Collections.singletonList(new RouteVariant(
                    new RoutePath("", true), Collections.emptySet(), Collections.emptyList())));
        }
    }

    private static final class RouteVariant {
        final RoutePath path;
        final Set<String> methods;
        final List<MappingProvenance> provenance;

        RouteVariant(RoutePath path, Collection<String> methods,
                     Collection<MappingProvenance> provenance) {
            this.path = path;
            this.methods = new TreeSet<>(methods);
            this.provenance = new ArrayList<>(provenance);
        }
    }

    private static final class RoutePath {
        final String value;
        final boolean isStatic;

        RoutePath(String value, boolean isStatic) {
            this.value = value;
            this.isStatic = isStatic;
        }
    }

    private static final class MappingSpec {
        final String annotation;
        final List<RoutePath> paths;
        final Set<String> methods;
        final String expression;
        final Long line;

        MappingSpec(String annotation, List<RoutePath> paths, Set<String> methods,
                    String expression, Long line) {
            this.annotation = annotation;
            this.paths = paths;
            this.methods = methods;
            this.expression = expression;
            this.line = line;
        }
    }

    private static final class MappingProvenance {
        final String level;
        final String annotation;
        final String expression;
        final String relativePath;
        final String symbol;
        final Long line;

        MappingProvenance(String level, MappingSpec mapping, SourceContext source,
                          String symbol) {
            this.level = level;
            this.annotation = mapping.annotation;
            this.expression = mapping.expression;
            this.relativePath = source.relativePath;
            this.symbol = symbol;
            this.line = mapping.line;
        }

        Map<String, Object> toMap() {
            Map<String, Object> result = linkedMap();
            result.put("level", level);
            result.put("annotation", annotation);
            result.put("expression", expression);
            result.put("relative_path", relativePath);
            result.put("symbol", symbol);
            result.put("line", line);
            return result;
        }
    }

    private static final class AnnotationInfo {
        final String name;
        final String expression;
        final Map<String, Object> attributes;

        AnnotationInfo(String name, String expression, Map<String, Object> attributes) {
            this.name = name;
            this.expression = expression;
            this.attributes = attributes;
        }

        Map<String, Object> toMap() {
            Map<String, Object> result = linkedMap();
            result.put("name", name);
            result.put("expression", expression);
            result.put("attributes", attributes);
            return result;
        }
    }

    private static final class AnnotationSourceIssue {
        final String code;
        final String message;
        final String symbol;
        final Long line;
        final String annotation;

        AnnotationSourceIssue(String code, String message, String symbol, Long line,
                              String annotation) {
            this.code = code;
            this.message = message;
            this.symbol = symbol;
            this.line = line;
            this.annotation = annotation;
        }
    }

    private static final class CustomConstraintDefinition {
        final String qualifiedName;
        final boolean constraintSourceConfirmed;

        CustomConstraintDefinition(String qualifiedName, boolean constraintSourceConfirmed) {
            this.qualifiedName = qualifiedName;
            this.constraintSourceConfirmed = constraintSourceConfirmed;
        }
    }

    private static final class ParameterScan {
        final List<ParameterInfo> parameters;
        final List<AnnotationSourceIssue> issues;

        ParameterScan(List<ParameterInfo> parameters, List<AnnotationSourceIssue> issues) {
            this.parameters = parameters;
            this.issues = issues;
        }
    }

    private static final class ValidationScan {
        final List<AnnotationInfo> validations;
        final List<AnnotationSourceIssue> issues;

        ValidationScan(List<AnnotationInfo> validations, List<AnnotationSourceIssue> issues) {
            this.validations = validations;
            this.issues = issues;
        }
    }

    private static final class ParameterInfo {
        final String name;
        final String type;
        final String location;
        final Boolean required;
        final List<AnnotationInfo> annotations;
        final Set<String> typeIdentifiers;

        ParameterInfo(String name, String type, String location, Boolean required,
                      List<AnnotationInfo> annotations, Set<String> typeIdentifiers) {
            this.name = name;
            this.type = type;
            this.location = location;
            this.required = required;
            this.annotations = annotations;
            this.typeIdentifiers = typeIdentifiers;
        }

        Map<String, Object> toMap() {
            Map<String, Object> result = linkedMap();
            result.put("name", name);
            result.put("type", type);
            result.put("location", location);
            result.put("required", required);
            List<Map<String, Object>> values = new ArrayList<>();
            for (AnnotationInfo annotation : annotations) {
                values.add(annotation.toMap());
            }
            result.put("annotations", values);
            return result;
        }
    }

    private static final class Endpoint {
        final String routeId;
        final String method;
        final String path;
        final boolean pathStatic;
        final String relativePath;
        final String symbol;
        final Long line;
        final Long endLine;
        final List<ParameterInfo> parameters;
        final List<String> mappingAnnotations;
        final List<MappingProvenance> mappingProvenance;
        final Set<String> referencedTypes;
        final List<Map<String, Object>> modelFields = new ArrayList<>();
        final Set<String> declaredPaths = new TreeSet<>();

        Endpoint(String method, String path, boolean pathStatic, SourceContext source,
                 String symbol, MethodTree methodTree, List<ParameterInfo> parameters,
                 List<MappingProvenance> mappingProvenance) {
            this.method = method;
            this.path = path;
            this.pathStatic = pathStatic;
            this.relativePath = source.relativePath;
            this.symbol = symbol;
            this.line = source.line(methodTree);
            this.endLine = source.endLine(methodTree);
            this.parameters = parameters;
            this.mappingProvenance = new ArrayList<>(mappingProvenance);
            this.mappingAnnotations = new ArrayList<>();
            for (MappingProvenance provenance : mappingProvenance) {
                this.mappingAnnotations.add(provenance.expression);
            }
            this.routeId = "route_" + sha256(method + "\u0000" + path + "\u0000"
                    + relativePath + "\u0000" + symbol).substring(0, 20);
            Set<String> types = new TreeSet<>();
            for (ParameterInfo parameter : parameters) {
                types.addAll(parameter.typeIdentifiers);
            }
            this.referencedTypes = types;
        }

        Map<String, Object> toMap() {
            Map<String, Object> result = linkedMap();
            result.put("route_id", routeId);
            result.put("framework", "spring-boot");
            result.put("method", method);
            result.put("path", path);
            result.put("declared_paths", new ArrayList<>(declaredPaths));
            result.put("path_is_static", pathStatic);
            result.put("relative_path", relativePath);
            result.put("symbol", symbol);
            result.put("line", line);
            result.put("end_line", endLine);
            result.put("mapping_annotations", mappingAnnotations);
            List<Map<String, Object>> provenanceValues = new ArrayList<>();
            for (MappingProvenance provenance : mappingProvenance) {
                provenanceValues.add(provenance.toMap());
            }
            result.put("mapping_provenance", provenanceValues);
            List<Map<String, Object>> parameterValues = new ArrayList<>();
            for (ParameterInfo parameter : parameters) {
                parameterValues.add(parameter.toMap());
            }
            result.put("parameters", parameterValues);
            result.put("model_fields", modelFields);
            return result;
        }
    }

    private static final class ModelField {
        final SourceContext source;
        final String classSimpleName;
        final String symbol;
        final String name;
        final String type;
        final Long line;
        final List<AnnotationInfo> validations;
        final List<AnnotationSourceIssue> validationIssues;
        final Set<String> referencedTypes;

        ModelField(SourceContext source, String classSimpleName, String symbol, VariableTree field,
                   List<AnnotationInfo> validations,
                   List<AnnotationSourceIssue> validationIssues) {
            this.source = source;
            this.classSimpleName = classSimpleName;
            this.symbol = symbol;
            this.name = field.getName().toString();
            this.type = field.getType() == null ? null : canonical(field.getType());
            this.line = source.line(field);
            this.validations = validations;
            this.validationIssues = validationIssues;
            this.referencedTypes = typeIdentifiers(field.getType());
        }

        Map<String, Object> toEndpointMap() {
            Map<String, Object> result = linkedMap();
            result.put("symbol", symbol);
            result.put("name", name);
            result.put("type", type);
            List<Map<String, Object>> values = new ArrayList<>();
            for (AnnotationInfo validation : validations) {
                values.add(validation.toMap());
            }
            result.put("validations", values);
            return result;
        }
    }

    private static final class EnumInfo {
        final SourceContext source;
        final String simpleName;
        final String symbol;
        final Long line;
        final List<String> values;

        EnumInfo(SourceContext source, String simpleName, String symbol, Long line,
                 List<String> values) {
            this.source = source;
            this.simpleName = simpleName;
            this.symbol = symbol;
            this.line = line;
            this.values = values;
        }
    }

    private static final class Evidence {
        final String evidenceId;
        final String logicalKey;
        final String logicalSlot;
        final String kind;
        final String relativePath;
        final String symbol;
        final Long line;
        final List<String> endpointIds;
        final Map<String, Object> details;

        Evidence(String evidenceId, String logicalKey, String logicalSlot, String kind,
                 SourceContext source, String symbol, Long line,
                 Collection<String> endpointIds,
                 Map<String, Object> details) {
            this.evidenceId = evidenceId;
            this.logicalKey = logicalKey;
            this.logicalSlot = logicalSlot;
            this.kind = kind;
            this.relativePath = source.relativePath;
            this.symbol = symbol;
            this.line = line;
            this.endpointIds = new ArrayList<>(new TreeSet<>(endpointIds));
            this.details = details;
        }

        Map<String, Object> toMap() {
            Map<String, Object> resultMap = linkedMap();
            resultMap.put("schema_version", SCHEMA_VERSION);
            resultMap.put("evidence_id", evidenceId);
            resultMap.put("logical_key", logicalKey);
            resultMap.put("logical_slot", logicalSlot);
            resultMap.put("framework", "spring-boot");
            resultMap.put("kind", kind);
            resultMap.put("relative_path", relativePath);
            resultMap.put("symbol", symbol);
            resultMap.put("line", line);
            resultMap.put("endpoint_ids", endpointIds);
            resultMap.put("details", details);
            return resultMap;
        }
    }

    private static final class State {
        final Config config;
        final List<Endpoint> endpoints = new ArrayList<>();
        final List<Evidence> evidence = new ArrayList<>();
        final List<ModelField> modelFields = new ArrayList<>();
        final List<EnumInfo> enums = new ArrayList<>();
        final List<Map<String, Object>> warnings = new ArrayList<>();
        final Map<String, CustomConstraintDefinition> customConstraints = new LinkedHashMap<>();
        final Set<String> controllerStereotypes = new TreeSet<>();
        final Map<String, Set<String>> controllerMetaAnnotations = new LinkedHashMap<>();
        final Set<String> parsedFiles = new TreeSet<>();
        final Map<String, Integer> evidenceCollisions = new HashMap<>();
        final Map<String, Integer> logicalSequences = new HashMap<>();

        State(Config config) {
            this.config = config;
        }

        void addEndpoint(Endpoint endpoint, SourceContext source, MethodTree method) {
            endpoints.add(endpoint);
            Map<String, Object> details = linkedMap();
            details.put("http_method", endpoint.method);
            details.put("path", endpoint.path);
            details.put("path_is_static", endpoint.pathStatic);
            details.put("mapping_annotations", endpoint.mappingAnnotations);
            List<Map<String, Object>> provenanceValues = new ArrayList<>();
            for (MappingProvenance provenance : endpoint.mappingProvenance) {
                provenanceValues.add(provenance.toMap());
            }
            details.put("mapping_provenance", provenanceValues);
            addEvidence("route.mapping", source, endpoint.symbol, source.line(method),
                    Collections.singletonList(endpoint.routeId), details);
        }

        void addEvidence(String kind, SourceContext source, String symbol, Long line,
                         Collection<String> endpointIds,
                         Map<String, Object> details) {
            List<String> sortedEndpointIds = new ArrayList<>(new TreeSet<>(endpointIds));
            if (sortedEndpointIds.size() > 1) {
                for (String endpointId : sortedEndpointIds) {
                    addEvidenceRecord(kind, source, symbol, line,
                            Collections.singletonList(endpointId), details);
                }
                return;
            }
            addEvidenceRecord(kind, source, symbol, line,
                    sortedEndpointIds, details);
        }

        private void addEvidenceRecord(String kind, SourceContext source, String symbol, Long line,
                                       Collection<String> endpointIds,
                                       Map<String, Object> details) {
            String endpointMaterial = String.join(",", new TreeSet<>(endpointIds));
            String baseMaterial = source.relativePath + "\u0000" + symbol + "\u0000" + kind
                    + "\u0000" + endpointMaterial + "\u0000" + Json.encode(details);
            int occurrence = evidenceCollisions.merge(baseMaterial, 1, Integer::sum);
            String material = occurrence == 1 ? baseMaterial : baseMaterial + "\u0000#" + occurrence;
            String evidenceId = "ev_" + sha256(material).substring(0, 24);
            String logicalBase = source.relativePath + "\u0000" + symbol + "\u0000" + kind
                    + "\u0000" + endpointMaterial;
            int logicalOccurrence = logicalSequences.merge(logicalBase, 1, Integer::sum);
            String logicalSlot = kind + "[" + logicalOccurrence + "]";
            String logicalKey = "evk_" + sha256(logicalBase + "\u0000" + logicalSlot)
                    .substring(0, 24);
            evidence.add(new Evidence(evidenceId, logicalKey, logicalSlot, kind, source, symbol, line,
                    endpointIds, details));
        }

        void addWarning(String code, String message, String path, String symbol) {
            Map<String, Object> warning = linkedMap();
            warning.put("code", code);
            warning.put("message", message);
            warning.put("path", path);
            warning.put("symbol", symbol);
            warnings.add(warning);
        }

        void addRouteActivationWarning(String message, SourceContext source, String symbol,
                                       Long line, List<AnnotationInfo> activations) {
            Map<String, Object> warning = linkedMap();
            warning.put("code", "SPRING_ROUTE_ACTIVATION_CONDITIONAL");
            warning.put("message", message);
            warning.put("path", source.relativePath);
            warning.put("symbol", symbol);
            warning.put("line", line);
            warning.put("disposition", "needs_confirmation");
            warning.put("affected_scope", "当前接口");
            warning.put("missing_evidence", Arrays.asList(
                    "resolved Spring profile/condition activation",
                    "runtime registered route inventory"));
            warning.put("next_action",
                    "resolve the active profile/condition and reconcile with Actuator/OpenAPI routes");
            warning.put("safe_resumption_point",
                    "resume endpoint discovery before generating route evidence");
            List<Map<String, Object>> values = new ArrayList<>();
            for (AnnotationInfo activation : activations) {
                values.add(activation.toMap());
            }
            warning.put("activation_annotations", values);
            warnings.add(warning);
        }

        void addAnnotationSourceWarning(String code, String message, SourceContext source,
                                        String symbol, Long line, String annotation) {
            Map<String, Object> warning = linkedMap();
            warning.put("code", code);
            warning.put("message", message);
            warning.put("path", source.relativePath);
            warning.put("symbol", symbol);
            warning.put("line", line);
            warning.put("annotation", annotation);
            warning.put("disposition", "needs_confirmation");
            warning.put("affected_scope", "全项目");
            warning.put("missing_evidence", Arrays.asList(
                    "framework annotation import provenance",
                    "resolved route registration semantics"));
            warning.put("next_action",
                    "use a confirmed Spring annotation import or inspect the custom annotation definition");
            warning.put("safe_resumption_point",
                    "resume endpoint discovery before generating route evidence");
            warnings.add(warning);
        }

        void addAnnotationSourceIssue(SourceContext source, AnnotationSourceIssue issue) {
            addAnnotationSourceWarning(issue.code, issue.message, source, issue.symbol,
                    issue.line, issue.annotation);
        }

        void addInterfaceAnalysisIssue(SourceContext source, AnnotationSourceIssue issue,
                                       Collection<Endpoint> linkedEndpoints) {
            if (linkedEndpoints.isEmpty()) {
                return;
            }
            Map<String, Object> warning = linkedMap();
            warning.put("code", issue.code);
            warning.put("message", issue.message);
            warning.put("path", source.relativePath);
            warning.put("symbol", issue.symbol);
            warning.put("line", issue.line);
            warning.put("annotation", issue.annotation);
            warning.put("disposition", "interface_analysis_gap");
            warning.put("affected_scope", "当前接口");
            warning.put("missing_evidence", Arrays.asList(
                    "effective request binding and Bean Validation semantics",
                    "runtime validation activation and exception mapping"));
            warning.put("next_action",
                    "trace the affected interface DTO, validators, active groups, and exception mapping");
            warning.put("safe_resumption_point",
                    "resume interface analysis without repeating route inventory discovery");
            List<String> endpointIds = new ArrayList<>();
            List<Map<String, Object>> endpoints = new ArrayList<>();
            for (Endpoint endpoint : linkedEndpoints) {
                endpointIds.add(endpoint.routeId);
                Map<String, Object> endpointReference = linkedMap();
                endpointReference.put("route_id", endpoint.routeId);
                endpointReference.put("method", endpoint.method);
                endpointReference.put("path", endpoint.path);
                endpoints.add(endpointReference);
            }
            warning.put("endpoint_ids", endpointIds);
            warning.put("endpoints", endpoints);
            if (endpoints.size() == 1) {
                warning.put("endpoint", endpoints.get(0));
            }
            warnings.add(warning);
        }

        CustomConstraintDefinition customConstraint(AnnotationTree annotation,
                                                    SourceContext source) {
            List<CustomConstraintDefinition> matches = new ArrayList<>();
            for (String candidate : source.annotationQualifiedCandidates(annotation)) {
                CustomConstraintDefinition definition = customConstraints.get(candidate);
                if (definition != null && !matches.contains(definition)) {
                    matches.add(definition);
                }
            }
            return matches.size() == 1 ? matches.get(0) : null;
        }

        void finishModelAndEnumEvidence() {
            Map<String, List<ModelField>> fieldsByOwnerType = new HashMap<>();
            for (ModelField field : modelFields) {
                fieldsByOwnerType.computeIfAbsent(field.classSimpleName, ignored -> new ArrayList<>())
                        .add(field);
            }

            Map<String, List<Endpoint>> endpointsByType = new HashMap<>();
            for (Endpoint endpoint : endpoints) {
                Set<String> reachableTypes = new TreeSet<>();
                Deque<String> pendingTypes = new ArrayDeque<>(endpoint.referencedTypes);
                Set<String> attachedFields = new HashSet<>();
                while (!pendingTypes.isEmpty()) {
                    String type = pendingTypes.removeFirst();
                    if (!reachableTypes.add(type)) {
                        continue;
                    }
                    for (ModelField field : fieldsByOwnerType.getOrDefault(
                            type, Collections.emptyList())) {
                        if (attachedFields.add(field.symbol)) {
                            endpoint.modelFields.add(field.toEndpointMap());
                        }
                        for (String referencedType : field.referencedTypes) {
                            if (!reachableTypes.contains(referencedType)) {
                                pendingTypes.addLast(referencedType);
                            }
                        }
                    }
                }
                for (String type : reachableTypes) {
                    endpointsByType.computeIfAbsent(type, ignored -> new ArrayList<>()).add(endpoint);
                }
            }

            for (ModelField field : modelFields) {
                if (field.validationIssues.isEmpty()) {
                    continue;
                }
                List<Endpoint> linked = endpointsByType.getOrDefault(
                        field.classSimpleName, Collections.emptyList());
                if (linked.isEmpty()) {
                    continue;
                }
                for (AnnotationSourceIssue issue : field.validationIssues) {
                    addInterfaceAnalysisIssue(field.source, issue, linked);
                }
            }

            for (ModelField field : modelFields) {
                List<Endpoint> linked = endpointsByType.getOrDefault(
                        field.classSimpleName, Collections.emptyList());
                Set<String> endpointIds = new TreeSet<>();
                for (Endpoint endpoint : linked) {
                    endpointIds.add(endpoint.routeId);
                }
                for (AnnotationInfo annotation : field.validations) {
                    Map<String, Object> details = linkedMap();
                    details.put("target", "field");
                    details.put("field", field.symbol);
                    details.put("field_type", field.type);
                    details.put("annotation", annotation.toMap());
                    addEvidence("validation.bean", field.source, field.symbol, field.line,
                            endpointIds, details);
                }
            }

            for (EnumInfo enumInfo : enums) {
                List<Endpoint> linked = endpointsByType.getOrDefault(
                        enumInfo.simpleName, Collections.emptyList());
                Set<String> endpointIds = new TreeSet<>();
                for (Endpoint endpoint : linked) {
                    endpointIds.add(endpoint.routeId);
                }
                Map<String, Object> details = linkedMap();
                details.put("enum", enumInfo.symbol);
                details.put("allowed_values", enumInfo.values);
                addEvidence("validation.enum", enumInfo.source, enumInfo.symbol, enumInfo.line,
                        endpointIds, details);
            }

            boolean hasBeanConstraints = modelFields.stream()
                    .anyMatch(field -> !field.validations.isEmpty()) || evidence.stream()
                    .anyMatch(item -> "validation.bean".equals(item.kind));
            if (hasBeanConstraints) {
                addWarning("BEAN_VALIDATION_RUNTIME_ACTIVATION_NOT_RESOLVED",
                        "Constraint annotations are reported from syntax, but the scanner does not "
                                + "prove runtime @Valid/@Validated wiring, validation groups, or a "
                                + "custom Validator configuration. Confirm activation before turning "
                                + "a constraint into an executable negative API case.",
                        null, null);
            }
        }

    }

    private static final class CustomConstraintCollector extends TreePathScanner<Void, Void> {
        private final State state;
        private final SourceContext source;
        private final Deque<String> classNames = new ArrayDeque<>();

        CustomConstraintCollector(State state, SourceContext source) {
            this.state = state;
            this.source = source;
        }

        @Override
        public Void visitClass(ClassTree node, Void unused) {
            classNames.addLast(node.getSimpleName().toString());
            if (node.getKind() == Tree.Kind.ANNOTATION_TYPE) {
                String nested = String.join(".", classNames);
                String annotationName = source.packageName.isEmpty() ? nested : source.packageName + "." + nested;
                Set<String> metaTypes = new TreeSet<>();
                state.controllerMetaAnnotations.put(annotationName, metaTypes);
                for (AnnotationTree annotation : node.getModifiers().getAnnotations()) {
                    metaTypes.addAll(source.annotationQualifiedCandidates(annotation));
                    String metaName = simpleName(annotation.getAnnotationType().toString());
                    if (("Controller".equals(metaName) && source.hasAnnotationSource(annotation, "org.springframework.stereotype"))
                            || ("RestController".equals(metaName) && source.hasAnnotationSource(annotation, "org.springframework.web.bind.annotation"))) {
                        state.controllerStereotypes.add(annotationName);
                    }
                    if (!"Constraint".equals(
                            simpleName(annotation.getAnnotationType().toString()))) {
                        continue;
                    }
                    String nestedName = String.join(".", classNames);
                    String qualifiedName = source.packageName.isEmpty()
                            ? nestedName : source.packageName + "." + nestedName;
                    boolean confirmed = source.hasAnnotationSource(
                            annotation, "jakarta.validation", "javax.validation");
                    state.customConstraints.put(qualifiedName,
                            new CustomConstraintDefinition(qualifiedName, confirmed));
                }
            }
            Void result = super.visitClass(node, unused);
            classNames.removeLast();
            return result;
        }
    }

    private static final class UnitCollector extends TreePathScanner<Void, Void> {
        private final State state;
        private final SourceContext source;
        private final Deque<String> classNames = new ArrayDeque<>();
        private final Deque<RouteContext> routeContexts = new ArrayDeque<>();
        private final Deque<List<AnnotationInfo>> routeActivationContexts = new ArrayDeque<>();
        private final Deque<Boolean> provenanceBlockedContexts = new ArrayDeque<>();
        private final Deque<Boolean> serverContexts = new ArrayDeque<>();
        private final Deque<Boolean> clientContexts = new ArrayDeque<>();

        UnitCollector(State state, SourceContext source) {
            this.state = state;
            this.source = source;
            this.routeContexts.push(RouteContext.root());
            this.routeActivationContexts.push(Collections.emptyList());
            this.provenanceBlockedContexts.push(false);
            this.serverContexts.push(false);
            this.clientContexts.push(false);
        }

        @Override
        public Void visitClass(ClassTree node, Void unused) {
            String className = node.getSimpleName().toString();
            classNames.addLast(className);
            String classSymbol = classSymbol();
            boolean server = false;
            boolean client = false;
            for (AnnotationTree annotation : node.getModifiers().getAnnotations()) {
                String name = simpleName(annotation.getAnnotationType().toString());
                server |= ("Controller".equals(name) && source.hasAnnotationSource(
                        annotation, "org.springframework.stereotype"))
                        || ("RestController".equals(name) && source.hasAnnotationSource(
                        annotation, "org.springframework.web.bind.annotation"));
                server |= !Collections.disjoint(source.annotationQualifiedCandidates(annotation),
                        state.controllerStereotypes);
                client |= "FeignClient".equals(name) && source.hasAnnotationSource(
                        annotation, "org.springframework.cloud.openfeign", "org.springframework.cloud.netflix.feign");
            }
            serverContexts.push(server);
            clientContexts.push(client);
            List<AnnotationSourceIssue> classIssues = annotationProvenanceIssues(
                    node.getModifiers(), classSymbol);
            int endpointStart = state.endpoints.size();
            provenanceBlockedContexts.push(
                    provenanceBlockedContexts.peek() || classIssues.stream()
                            .anyMatch(UnitCollector::blocksRouteInventory));
            RouteContext parent = routeContexts.peek();
            warnUnresolvedMappingAnnotations(node.getModifiers(), classSymbol);
            List<MappingSpec> classMappings = mappingAnnotations(node.getModifiers(), source);
            if (node.getKind() == Tree.Kind.ANNOTATION_TYPE && !classMappings.isEmpty()) {
                state.addAnnotationSourceWarning(
                        "SPRING_META_MAPPING_UNSUPPORTED",
                        "custom annotation type declares a Spring mapping meta-annotation; "
                                + "composed route expansion is unsupported",
                        source, classSymbol, source.line(node), classMappings.get(0).expression);
            }
            RouteContext current = classMappings.isEmpty()
                    ? parent : applyMappings(parent, classMappings, source, classSymbol, state,
                    "class");
            routeContexts.push(current);
            List<AnnotationInfo> classActivations = new ArrayList<>(
                    routeActivationContexts.peek());
            classActivations.addAll(routeActivationAnnotations(node.getModifiers(), source));
            routeActivationContexts.push(classActivations);

            collectModelFields(node, className, classSymbol);
            if (node.getKind() == Tree.Kind.ENUM) {
                collectEnum(node, className, classSymbol);
            }
            collectResponseStatusAnnotation(node.getModifiers(), classSymbol, source.line(node),
                    Collections.emptyList());

            Void result = super.visitClass(node, unused);
            List<Endpoint> classEndpoints = new ArrayList<>(
                    state.endpoints.subList(endpointStart, state.endpoints.size()));
            for (AnnotationSourceIssue issue : classIssues) {
                if (blocksRouteInventory(issue)) {
                    state.addAnnotationSourceIssue(source, issue);
                } else {
                    state.addInterfaceAnalysisIssue(source, issue, classEndpoints);
                }
            }
            routeActivationContexts.pop();
            routeContexts.pop();
            provenanceBlockedContexts.pop();
            serverContexts.pop();
            clientContexts.pop();
            classNames.removeLast();
            return result;
        }

        @Override
        public Void visitMethod(MethodTree node, Void unused) {
            String symbol = methodSymbol(node);
            warnUnresolvedMappingAnnotations(node.getModifiers(), symbol);
            List<MappingSpec> methodMappings = mappingAnnotations(node.getModifiers(), source);
            ParameterScan parameterScan = parameterInfos(node, symbol);
            List<ParameterInfo> parameters = parameterScan.parameters;
            List<AnnotationSourceIssue> methodIssues = new ArrayList<>(
                    annotationProvenanceIssues(node.getModifiers(), symbol));
            boolean provenanceBlocked = provenanceBlockedContexts.peek()
                    || (!methodMappings.isEmpty() && methodIssues.stream()
                            .anyMatch(UnitCollector::blocksRouteInventory));
            List<String> endpointIds = new ArrayList<>();
            List<Endpoint> linkedEndpoints = new ArrayList<>();
            List<AnnotationInfo> routeActivations = new ArrayList<>(
                    routeActivationContexts.peek());
            routeActivations.addAll(routeActivationAnnotations(node.getModifiers(), source));

            if (!methodMappings.isEmpty() && clientContexts.peek() && !serverContexts.peek()) {
                state.addWarning("SPRING_CLIENT_DECLARATION_SKIPPED",
                        "Feign client mapping is not a server endpoint", source.relativePath, symbol);
            } else if (!methodMappings.isEmpty() && !serverContexts.peek() && !provenanceBlocked) {
                state.addWarning("SPRING_SERVER_REGISTRATION_UNRESOLVED",
                        "mapping has no confirmed server registration; inspect composed controller annotations, inheritance or runtime registration",
                        source.relativePath, symbol);
            } else if (!methodMappings.isEmpty() && provenanceBlocked) {
                // A same-named annotation without proven framework provenance
                // makes the endpoint contract unsafe to infer.
            } else if (!methodMappings.isEmpty() && !routeActivations.isEmpty()) {
                state.addRouteActivationWarning(
                        "Spring route has @Profile/@Conditional* activation that the parse-only "
                                + "AST scan cannot resolve; endpoint inference was skipped",
                        source, symbol, source.line(node), routeActivations);
            } else if (!methodMappings.isEmpty()) {
                RouteContext resolved = applyMappings(
                        routeContexts.peek(), methodMappings, source, symbol, state, "method");
                Map<String, Endpoint> methodEndpoints = new LinkedHashMap<>();
                for (RouteVariant variant : resolved.variants) {
                    RoutePath routePath = variant.path;
                    String normalizedPath = normalizeRoutePath(routePath.value);
                    if (!routePath.isStatic) {
                        state.addWarning("DYNAMIC_ROUTE_UNRESOLVED",
                                "Dynamic route path was skipped because its HTTP path cannot be proven: "
                                        + routePath.value,
                                source.relativePath, symbol);
                        continue;
                    }
                    if (!routeMatchesPrefix(normalizedPath, state.config.routePrefix)) {
                        continue;
                    }
                    Set<String> methods = variant.methods.isEmpty()
                            ? Collections.singleton("ANY") : variant.methods;
                    for (String method : methods) {
                        String identity = method + "\u0000" + normalizedPath;
                        Endpoint existing = methodEndpoints.get(identity);
                        if (existing != null) {
                            existing.declaredPaths.add(routePath.value);
                            continue;
                        }
                        Endpoint endpoint = new Endpoint(method, normalizedPath, routePath.isStatic,
                                source, symbol, node, parameters, variant.provenance);
                        endpoint.declaredPaths.add(routePath.value);
                        methodEndpoints.put(identity, endpoint);
                        state.addEndpoint(endpoint, source, node);
                        endpointIds.add(endpoint.routeId);
                        linkedEndpoints.add(endpoint);
                    }
                }
            }

            if (!methodMappings.isEmpty()) {
                for (AnnotationSourceIssue issue : methodIssues) {
                    if (blocksRouteInventory(issue)) {
                        state.addAnnotationSourceIssue(source, issue);
                    } else {
                        state.addInterfaceAnalysisIssue(source, issue, linkedEndpoints);
                    }
                }
                for (AnnotationSourceIssue issue : parameterScan.issues) {
                    state.addInterfaceAnalysisIssue(source, issue, linkedEndpoints);
                }
            }

            if (!endpointIds.isEmpty()) {
                collectParameterValidationEvidence(node, parameters, endpointIds, symbol);
            }
            if (methodMappings.isEmpty() || !endpointIds.isEmpty()) {
                collectResponseStatusAnnotation(
                        node.getModifiers(), symbol, source.line(node), endpointIds);
            }
            return null;
        }

        private static boolean blocksRouteInventory(AnnotationSourceIssue issue) {
            return "SPRING_CONTROLLER_ANNOTATION_SOURCE_UNRESOLVED".equals(issue.code)
                    || "SPRING_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED".equals(issue.code);
        }

        private void warnUnresolvedMappingAnnotations(ModifiersTree modifiers, String symbol) {
            for (AnnotationTree annotation : modifiers.getAnnotations()) {
                String name = simpleName(annotation.getAnnotationType().toString());
                if (!MAPPING_ANNOTATIONS.contains(name)
                        || source.hasAnnotationSource(annotation,
                        "org.springframework.web.bind.annotation")) {
                    continue;
                }
                state.addAnnotationSourceWarning(
                        "SPRING_MAPPING_ANNOTATION_SOURCE_UNRESOLVED",
                        "route-like annotation has no confirmed Spring Web import; it was not "
                                + "treated as a mapping",
                        source, symbol, source.line(annotation), canonical(annotation));
            }
        }

        private void collectModelFields(ClassTree node, String className, String classSymbol) {
            for (Tree member : node.getMembers()) {
                if (!(member instanceof VariableTree)) {
                    continue;
                }
                VariableTree field = (VariableTree) member;
                if (isEnumConstant(field, className)) {
                    continue;
                }
                String fieldSymbol = classSymbol + "." + field.getName();
                ValidationScan validationScan = validationAnnotations(
                        field.getModifiers(), fieldSymbol);
                if (!validationScan.validations.isEmpty()
                        || !validationScan.issues.isEmpty()) {
                    state.modelFields.add(new ModelField(source, className,
                            fieldSymbol, field, validationScan.validations,
                            validationScan.issues));
                }
            }
        }

        private void collectEnum(ClassTree node, String className, String classSymbol) {
            List<String> values = new ArrayList<>();
            for (Tree member : node.getMembers()) {
                if (member instanceof VariableTree && isEnumConstant((VariableTree) member, className)) {
                    values.add(((VariableTree) member).getName().toString());
                }
            }
            if (!values.isEmpty()) {
                state.enums.add(new EnumInfo(source, className, classSymbol, source.line(node), values));
            }
        }

        private void collectParameterValidationEvidence(MethodTree node,
                                                        List<ParameterInfo> parameters,
                                                        List<String> endpointIds,
                                                        String symbol) {
            for (int index = 0; index < node.getParameters().size(); index++) {
                VariableTree parameterTree = node.getParameters().get(index);
                ParameterInfo parameter = parameters.get(index);
                for (AnnotationInfo annotation : parameter.annotations) {
                    if (!VALIDATION_ANNOTATIONS.contains(annotation.name)) {
                        continue;
                    }
                    Map<String, Object> details = linkedMap();
                    details.put("target", "parameter");
                    details.put("parameter", parameter.name);
                    details.put("parameter_type", parameter.type);
                    details.put("location", parameter.location);
                    details.put("annotation", annotation.toMap());
                    state.addEvidence("validation.bean", source, symbol,
                            source.line(parameterTree), endpointIds, details);
                }
            }
        }

        private void collectResponseStatusAnnotation(ModifiersTree modifiers, String symbol,
                                                     Long line, Collection<String> endpointIds) {
            for (AnnotationTree annotation : modifiers.getAnnotations()) {
                if (!"ResponseStatus".equals(
                        simpleName(annotation.getAnnotationType().toString()))
                        || !source.hasAnnotationSource(
                        annotation, "org.springframework.web.bind.annotation")) {
                    continue;
                }
                AnnotationInfo info = annotationInfo(annotation);
                Map<String, Object> details = linkedMap();
                details.put("annotation", info.toMap());
                state.addEvidence("response.status", source, symbol, line,
                        endpointIds, details);
            }
        }

        private ParameterScan parameterInfos(MethodTree method, String methodSymbol) {
            List<ParameterInfo> result = new ArrayList<>();
            List<AnnotationSourceIssue> issues = new ArrayList<>();
            for (VariableTree parameter : method.getParameters()) {
                List<AnnotationInfo> annotations = new ArrayList<>();
                String location = "argument";
                Boolean required = null;
                String parameterSymbol = methodSymbol + "." + parameter.getName();
                for (AnnotationTree annotationTree
                        : parameter.getModifiers().getAnnotations()) {
                    AnnotationInfo annotation = annotationInfo(annotationTree);
                    AnnotationSourceIssue semanticIssue = validationSemanticIssue(
                            annotationTree, parameterSymbol);
                    if (semanticIssue != null) {
                        issues.add(semanticIssue);
                        continue;
                    }
                    if (REQUEST_BINDING_LOCATIONS.containsKey(annotation.name)) {
                        if (!source.hasAnnotationSource(annotationTree,
                                "org.springframework.web.bind.annotation")) {
                            issues.add(new AnnotationSourceIssue(
                                    "SPRING_REQUEST_BINDING_ANNOTATION_SOURCE_UNRESOLVED",
                                    "request-binding annotation has no confirmed Spring Web "
                                            + "provenance; endpoint contract inference was skipped",
                                    parameterSymbol, source.line(annotationTree),
                                    canonical(annotationTree)));
                            continue;
                        }
                        annotations.add(annotation);
                        location = REQUEST_BINDING_LOCATIONS.get(annotation.name);
                        Object explicitRequired = annotation.attributes.get("required");
                        if (explicitRequired instanceof Boolean) {
                            required = (Boolean) explicitRequired;
                        }
                        continue;
                    }
                    if (VALIDATION_ANNOTATIONS.contains(annotation.name)) {
                        if (!source.hasAnnotationSource(annotationTree,
                                "jakarta.validation.constraints",
                                "javax.validation.constraints")) {
                            issues.add(new AnnotationSourceIssue(
                                    "SPRING_VALIDATION_ANNOTATION_SOURCE_UNRESOLVED",
                                    "built-in Bean Validation annotation has no confirmed "
                                            + "Jakarta/Javax constraints provenance; validation "
                                            + "evidence was skipped",
                                    parameterSymbol, source.line(annotationTree),
                                    canonical(annotationTree)));
                            continue;
                        }
                        annotations.add(annotation);
                        if (Arrays.asList("NotNull", "NotBlank", "NotEmpty")
                                .contains(annotation.name)) {
                            required = true;
                        }
                        continue;
                    }
                    CustomConstraintDefinition custom = state.customConstraint(
                            annotationTree, source);
                    if (custom != null) {
                        issues.add(customConstraintIssue(
                                custom, parameterSymbol, annotationTree));
                        continue;
                    }
                    annotations.add(annotation);
                }
                result.add(new ParameterInfo(parameter.getName().toString(),
                        parameter.getType() == null ? null : canonical(parameter.getType()),
                        location, required, annotations,
                        typeIdentifiers(parameter.getType())));
            }
            return new ParameterScan(result, issues);
        }

        private ValidationScan validationAnnotations(ModifiersTree modifiers, String symbol) {
            List<AnnotationInfo> validations = new ArrayList<>();
            List<AnnotationSourceIssue> issues = new ArrayList<>();
            for (AnnotationTree annotationTree : modifiers.getAnnotations()) {
                AnnotationInfo annotation = annotationInfo(annotationTree);
                AnnotationSourceIssue semanticIssue = validationSemanticIssue(
                        annotationTree, symbol);
                if (semanticIssue != null) {
                    issues.add(semanticIssue);
                    continue;
                }
                if (VALIDATION_ANNOTATIONS.contains(annotation.name)) {
                    if (source.hasAnnotationSource(annotationTree,
                            "jakarta.validation.constraints",
                            "javax.validation.constraints")) {
                        validations.add(annotation);
                    } else {
                        issues.add(new AnnotationSourceIssue(
                                "SPRING_VALIDATION_ANNOTATION_SOURCE_UNRESOLVED",
                                "built-in Bean Validation annotation has no confirmed "
                                        + "Jakarta/Javax constraints provenance; validation "
                                        + "evidence was skipped",
                                symbol, source.line(annotationTree),
                                canonical(annotationTree)));
                    }
                    continue;
                }
                CustomConstraintDefinition custom = state.customConstraint(
                        annotationTree, source);
                if (custom != null) {
                    issues.add(customConstraintIssue(custom, symbol, annotationTree));
                }
            }
            return new ValidationScan(validations, issues);
        }

        private AnnotationSourceIssue validationSemanticIssue(
                AnnotationTree annotation, String symbol) {
            String name = simpleName(annotation.getAnnotationType().toString());
            Map<String, ExpressionTree> arguments = annotationArguments(annotation);
            if ("Validated".equals(name)) {
                if (!source.hasAnnotationSource(
                        annotation, "org.springframework.validation.annotation")) {
                    return new AnnotationSourceIssue(
                            "SPRING_VALIDATION_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED",
                            "Validated annotation has no confirmed Spring provenance; "
                                    + "validation activation was not inferred",
                            symbol, source.line(annotation), canonical(annotation));
                }
                if (!arguments.isEmpty()) {
                    return new AnnotationSourceIssue(
                            "SPRING_VALIDATION_GROUP_SEMANTICS_UNRESOLVED",
                            "@Validated selects validation groups that the AST adapter "
                                    + "cannot expand into an effective constraint set",
                            symbol, source.line(annotation), canonical(annotation));
                }
                return null;
            }
            if ("Valid".equals(name)) {
                if (!source.hasAnnotationSource(
                        annotation, "jakarta.validation", "javax.validation")) {
                    return new AnnotationSourceIssue(
                            "SPRING_VALIDATION_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED",
                            "Valid annotation has no confirmed Jakarta/Javax provenance; "
                                    + "cascaded validation was not inferred",
                            symbol, source.line(annotation), canonical(annotation));
                }
                return new AnnotationSourceIssue(
                        "SPRING_VALIDATION_CASCADE_SEMANTICS_UNRESOLVED",
                        "cascaded @Valid constraints cannot be expanded accurately by the "
                                + "parse-only AST adapter",
                        symbol, source.line(annotation), canonical(annotation));
            }
            if ("ConvertGroup".equals(name)) {
                if (!source.hasAnnotationSource(annotation,
                        "jakarta.validation.groups", "javax.validation.groups")) {
                    return new AnnotationSourceIssue(
                            "SPRING_VALIDATION_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED",
                            "ConvertGroup annotation has no confirmed Jakarta/Javax "
                                    + "provenance; group conversion was not inferred",
                            symbol, source.line(annotation), canonical(annotation));
                }
                return new AnnotationSourceIssue(
                        "SPRING_VALIDATION_GROUP_SEMANTICS_UNRESOLVED",
                        "@ConvertGroup changes the effective validation group and requires "
                                + "runtime validation semantics",
                        symbol, source.line(annotation), canonical(annotation));
            }
            if (VALIDATION_ANNOTATIONS.contains(name)
                    && source.hasAnnotationSource(annotation,
                    "jakarta.validation.constraints", "javax.validation.constraints")
                    && (arguments.containsKey("groups")
                    || arguments.containsKey("payload"))) {
                return new AnnotationSourceIssue(
                        "SPRING_VALIDATION_GROUP_SEMANTICS_UNRESOLVED",
                        "constraint groups/payload alter the effective validation set that "
                                + "the AST adapter cannot expand",
                        symbol, source.line(annotation), canonical(annotation));
            }
            return null;
        }

        private AnnotationSourceIssue customConstraintIssue(
                CustomConstraintDefinition definition, String symbol,
                AnnotationTree annotation) {
            if (!definition.constraintSourceConfirmed) {
                return new AnnotationSourceIssue(
                        "SPRING_CUSTOM_CONSTRAINT_SOURCE_UNRESOLVED",
                        "source-defined constraint uses an unconfirmed @Constraint "
                                + "meta-annotation; validation semantics were skipped",
                        symbol, source.line(annotation), canonical(annotation));
            }
            return new AnnotationSourceIssue(
                    "SPRING_CUSTOM_CONSTRAINT_SEMANTICS_UNRESOLVED",
                    "custom Bean Validation constraint requires its validator and runtime "
                            + "activation before API-case inference",
                    symbol, source.line(annotation), canonical(annotation));
        }

        private List<AnnotationSourceIssue> annotationProvenanceIssues(
                ModifiersTree modifiers, String symbol) {
            List<AnnotationSourceIssue> issues = new ArrayList<>();
            for (AnnotationTree annotation : modifiers.getAnnotations()) {
                String name = simpleName(annotation.getAnnotationType().toString());
                AnnotationSourceIssue validationIssue = validationSemanticIssue(
                        annotation, symbol);
                if (validationIssue != null) {
                    issues.add(validationIssue);
                    continue;
                }
                CustomConstraintDefinition custom = state.customConstraint(
                        annotation, source);
                if (custom != null) {
                    issues.add(customConstraintIssue(custom, symbol, annotation));
                    continue;
                }
                if (VALIDATION_ANNOTATIONS.contains(name)
                        && !source.hasAnnotationSource(annotation,
                        "jakarta.validation.constraints",
                        "javax.validation.constraints")) {
                    issues.add(new AnnotationSourceIssue(
                            "SPRING_VALIDATION_ANNOTATION_SOURCE_UNRESOLVED",
                            "built-in Bean Validation annotation has no confirmed "
                                    + "Jakarta/Javax constraints provenance; validation "
                                    + "evidence was skipped",
                            symbol, source.line(annotation), canonical(annotation)));
                    continue;
                }
                if (CONTROLLER_ANNOTATIONS.contains(name)) {
                    boolean confirmed = "Controller".equals(name)
                            ? source.hasAnnotationSource(
                            annotation, "org.springframework.stereotype")
                            : source.hasAnnotationSource(
                            annotation, "org.springframework.web.bind.annotation");
                    if (!confirmed) {
                        issues.add(new AnnotationSourceIssue(
                                "SPRING_CONTROLLER_ANNOTATION_SOURCE_UNRESOLVED",
                                "controller annotation has no confirmed official Spring "
                                        + "provenance; endpoint inference was skipped",
                                symbol, source.line(annotation), canonical(annotation)));
                    }
                    continue;
                }
                if ("ResponseStatus".equals(name)
                        && !source.hasAnnotationSource(
                        annotation, "org.springframework.web.bind.annotation")) {
                    issues.add(new AnnotationSourceIssue(
                            "SPRING_RESPONSE_STATUS_ANNOTATION_SOURCE_UNRESOLVED",
                            "ResponseStatus annotation has no confirmed Spring Web "
                                    + "provenance; response-contract evidence was skipped",
                            symbol, source.line(annotation), canonical(annotation)));
                    continue;
                }
                boolean activationName = "Profile".equals(name)
                        || name.startsWith("Conditional");
                if (!activationName) {
                    continue;
                }
                boolean confirmed = "Profile".equals(name)
                        ? source.hasAnnotationSource(
                        annotation, "org.springframework.context.annotation")
                        : (("Conditional".equals(name)
                        && source.hasAnnotationSource(
                        annotation, "org.springframework.context.annotation"))
                        || source.hasAnnotationSource(annotation,
                        "org.springframework.boot.autoconfigure.condition"));
                if (!confirmed) {
                    issues.add(new AnnotationSourceIssue(
                            "SPRING_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED",
                            "Profile/Conditional annotation has no confirmed Spring/Boot "
                                    + "provenance; endpoint activation inference was skipped",
                            symbol, source.line(annotation), canonical(annotation)));
                }
            }
            return issues;
        }

        private String classSymbol() {
            String nested = String.join(".", classNames);
            return source.packageName.isEmpty() ? nested : source.packageName + "." + nested;
        }

        private String methodSymbol(MethodTree method) {
            StringBuilder builder = new StringBuilder(classSymbol())
                    .append('#').append(method.getName()).append('(');
            for (int index = 0; index < method.getParameters().size(); index++) {
                if (index > 0) {
                    builder.append(',');
                }
                VariableTree parameter = method.getParameters().get(index);
                builder.append(parameter.getType() == null ? "?" : canonical(parameter.getType()));
            }
            return builder.append(')').toString();
        }
    }

    private static List<MappingSpec> mappingAnnotations(ModifiersTree modifiers,
                                                        SourceContext source) {
        List<MappingSpec> result = new ArrayList<>();
        for (AnnotationTree annotation : modifiers.getAnnotations()) {
            String name = simpleName(annotation.getAnnotationType().toString());
            if (!MAPPING_ANNOTATIONS.contains(name)
                    || !source.hasAnnotationSource(annotation,
                    "org.springframework.web.bind.annotation")) {
                continue;
            }
            Map<String, ExpressionTree> arguments = annotationArguments(annotation);
            ExpressionTree pathExpression = arguments.containsKey("path")
                    ? arguments.get("path") : arguments.get("value");
            List<RoutePath> paths = routePathValues(pathExpression);
            if (paths.isEmpty()) {
                paths = Collections.singletonList(new RoutePath("", true));
            }
            Set<String> methods = new TreeSet<>();
            if (FIXED_MAPPING_METHODS.containsKey(name)) {
                methods.add(FIXED_MAPPING_METHODS.get(name));
            } else {
                methods.addAll(requestMethodValues(arguments.get("method")));
            }
            result.add(new MappingSpec(name, paths, methods, canonical(annotation),
                    source.line(annotation)));
        }
        return result;
    }

    private static RouteContext applyMappings(RouteContext parent, List<MappingSpec> mappings,
                                              SourceContext source, String symbol, State state,
                                              String level) {
        List<RouteVariant> variants = new ArrayList<>();
        boolean hadMethodConflict = false;
        for (RouteVariant parentVariant : parent.variants) {
            for (MappingSpec mapping : mappings) {
                Set<String> combinedMethods = combineMethods(
                        parentVariant.methods, mapping.methods);
                if (!parentVariant.methods.isEmpty() && !mapping.methods.isEmpty()
                        && combinedMethods.isEmpty()) {
                    hadMethodConflict = true;
                    continue;
                }
                List<MappingProvenance> provenance = new ArrayList<>(parentVariant.provenance);
                provenance.add(new MappingProvenance(level, mapping, source, symbol));
                for (RoutePath suffix : mapping.paths) {
                    variants.add(new RouteVariant(
                            new RoutePath(
                                    joinRoutePaths(parentVariant.path.value, suffix.value),
                                    parentVariant.path.isStatic && suffix.isStatic),
                            combinedMethods,
                            provenance));
                }
            }
        }
        if (variants.isEmpty() && hadMethodConflict) {
            state.addWarning("REQUEST_METHOD_CONFLICT",
                    "Class-level and method-level mapping HTTP methods have no intersection.",
                    source.relativePath, symbol);
        }
        return new RouteContext(deduplicateVariants(variants));
    }

    private static Set<String> combineMethods(Set<String> parent, Set<String> child) {
        if (parent.isEmpty()) {
            return new TreeSet<>(child);
        }
        if (child.isEmpty()) {
            return new TreeSet<>(parent);
        }
        Set<String> intersection = new TreeSet<>(parent);
        intersection.retainAll(child);
        return intersection;
    }

    private static List<RouteVariant> deduplicateVariants(List<RouteVariant> values) {
        Map<String, RouteVariant> result = new LinkedHashMap<>();
        for (RouteVariant value : values) {
            String key = value.path.value + "\u0000" + value.path.isStatic
                    + "\u0000" + String.join(",", value.methods);
            result.putIfAbsent(key, value);
        }
        return new ArrayList<>(result.values());
    }

    private static List<RoutePath> routePathValues(ExpressionTree expression) {
        if (expression == null) {
            return Collections.emptyList();
        }
        if (expression instanceof NewArrayTree) {
            List<RoutePath> values = new ArrayList<>();
            List<? extends ExpressionTree> initializers = ((NewArrayTree) expression).getInitializers();
            if (initializers != null) {
                for (ExpressionTree initializer : initializers) {
                    values.add(routePathValue(initializer));
                }
            }
            return values;
        }
        return Collections.singletonList(routePathValue(expression));
    }

    private static RoutePath routePathValue(ExpressionTree expression) {
        String staticValue = staticString(expression);
        if (staticValue != null) {
            return new RoutePath(staticValue, true);
        }
        return new RoutePath("<dynamic:" + canonical(expression) + ">", false);
    }

    private static String staticString(Tree tree) {
        if (tree instanceof LiteralTree) {
            Object value = ((LiteralTree) tree).getValue();
            return value instanceof String ? (String) value : null;
        }
        if (tree instanceof BinaryTree && tree.getKind() == Tree.Kind.PLUS) {
            String left = staticString(((BinaryTree) tree).getLeftOperand());
            String right = staticString(((BinaryTree) tree).getRightOperand());
            return left != null && right != null ? left + right : null;
        }
        return null;
    }

    private static Set<String> requestMethodValues(ExpressionTree expression) {
        Set<String> methods = new TreeSet<>();
        if (expression == null) {
            return methods;
        }
        if (expression instanceof NewArrayTree) {
            List<? extends ExpressionTree> initializers = ((NewArrayTree) expression).getInitializers();
            if (initializers != null) {
                for (ExpressionTree initializer : initializers) {
                    methods.add(requestMethodValue(initializer));
                }
            }
        } else {
            methods.add(requestMethodValue(expression));
        }
        methods.remove("");
        return methods;
    }

    private static String requestMethodValue(ExpressionTree expression) {
        if (expression instanceof MemberSelectTree) {
            return ((MemberSelectTree) expression).getIdentifier().toString().toUpperCase(Locale.ROOT);
        }
        if (expression instanceof IdentifierTree) {
            return ((IdentifierTree) expression).getName().toString().toUpperCase(Locale.ROOT);
        }
        return canonical(expression).toUpperCase(Locale.ROOT);
    }

    private static Map<String, ExpressionTree> annotationArguments(AnnotationTree annotation) {
        Map<String, ExpressionTree> result = new LinkedHashMap<>();
        int positional = 0;
        for (ExpressionTree argument : annotation.getArguments()) {
            if (argument instanceof AssignmentTree) {
                AssignmentTree assignment = (AssignmentTree) argument;
                result.put(assignment.getVariable().toString(), assignment.getExpression());
            } else {
                result.put(positional == 0 ? "value" : "$" + positional, argument);
                positional++;
            }
        }
        return result;
    }

    private static List<AnnotationInfo> routeActivationAnnotations(ModifiersTree modifiers,
                                                                   SourceContext source) {
        List<AnnotationInfo> result = new ArrayList<>();
        for (AnnotationTree annotation : modifiers.getAnnotations()) {
            AnnotationInfo info = annotationInfo(annotation);
            boolean springProfile = "Profile".equals(info.name)
                    && source.hasAnnotationSource(annotation,
                    "org.springframework.context.annotation");
            boolean springConditional = ("Conditional".equals(info.name)
                    && source.hasAnnotationSource(annotation,
                    "org.springframework.context.annotation"))
                    || (info.name.startsWith("Conditional")
                    && source.hasAnnotationSource(annotation,
                    "org.springframework.boot.autoconfigure.condition"));
            if (springProfile || springConditional) {
                result.add(info);
            }
        }
        return result;
    }

    private static AnnotationInfo annotationInfo(AnnotationTree annotation) {
        Map<String, Object> attributes = linkedMap();
        for (Map.Entry<String, ExpressionTree> entry : annotationArguments(annotation).entrySet()) {
            attributes.put(entry.getKey(), staticAnnotationValue(entry.getValue()));
        }
        return new AnnotationInfo(simpleName(annotation.getAnnotationType().toString()),
                canonical(annotation), attributes);
    }

    private static Object staticAnnotationValue(ExpressionTree expression) {
        if (expression instanceof LiteralTree) {
            return ((LiteralTree) expression).getValue();
        }
        if (expression instanceof NewArrayTree) {
            List<Object> values = new ArrayList<>();
            List<? extends ExpressionTree> initializers = ((NewArrayTree) expression).getInitializers();
            if (initializers != null) {
                for (ExpressionTree initializer : initializers) {
                    values.add(staticAnnotationValue(initializer));
                }
            }
            return values;
        }
        String string = staticString(expression);
        return string != null ? string : canonical(expression);
    }

    private static Set<String> typeIdentifiers(Tree typeTree) {
        Set<String> result = new TreeSet<>();
        if (typeTree == null) {
            return result;
        }
        String value = canonical(typeTree);
        StringBuilder token = new StringBuilder();
        for (int index = 0; index <= value.length(); index++) {
            char character = index < value.length() ? value.charAt(index) : ' ';
            if (Character.isJavaIdentifierPart(character)) {
                token.append(character);
            } else if (token.length() > 0) {
                String name = token.toString();
                if (Character.isUpperCase(name.charAt(0)) && !BUILTIN_TYPE_NAMES.contains(name)) {
                    result.add(name);
                }
                token.setLength(0);
            }
        }
        return result;
    }

    private static boolean isEnumConstant(VariableTree field, String enumName) {
        if (!(field.getInitializer() instanceof NewClassTree) || field.getType() == null) {
            return false;
        }
        return enumName.equals(simpleName(canonical(field.getType())));
    }

    private static String joinRoutePaths(String prefix, String suffix) {
        if (prefix == null || prefix.isEmpty()) {
            return suffix == null ? "" : suffix;
        }
        if (suffix == null || suffix.isEmpty()) {
            return prefix;
        }
        int prefixEnd = prefix.length();
        while (prefixEnd > 0 && prefix.charAt(prefixEnd - 1) == '/') {
            prefixEnd--;
        }
        int suffixStart = 0;
        while (suffixStart < suffix.length() && suffix.charAt(suffixStart) == '/') {
            suffixStart++;
        }
        return prefix.substring(0, prefixEnd) + "/" + suffix.substring(suffixStart);
    }

    private static String normalizeRoutePath(String value) {
        if (value == null || value.isEmpty()) {
            return "/";
        }
        StringBuilder result = new StringBuilder();
        boolean previousSlash = false;
        if (value.charAt(0) != '/') {
            result.append('/');
            previousSlash = true;
        }
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            if (character == '/') {
                if (!previousSlash) {
                    result.append(character);
                }
                previousSlash = true;
            } else {
                result.append(character);
                previousSlash = false;
            }
        }
        if (result.length() > 1 && result.charAt(result.length() - 1) == '/') {
            result.setLength(result.length() - 1);
        }
        return result.toString();
    }

    private static boolean routeMatchesPrefix(String path, String prefix) {
        if (prefix == null || prefix.trim().isEmpty()) {
            return true;
        }
        String normalizedPath = normalizeRoutePath(path);
        String normalizedPrefix = normalizeRoutePath(prefix);
        if ("/".equals(normalizedPrefix)) {
            return true;
        }
        return normalizedPath.equals(normalizedPrefix)
                || normalizedPath.startsWith(normalizedPrefix + "/");
    }

    private static String simpleName(String value) {
        int dot = value.lastIndexOf('.');
        return dot >= 0 ? value.substring(dot + 1) : value;
    }

    /** Canonical text is derived from Tree.toString(), never from source regex matching. */
    private static String canonical(Tree tree) {
        return tree == null ? "" : canonicalText(tree.toString());
    }

    private static String canonicalText(String value) {
        if (value == null) {
            return "";
        }
        StringBuilder result = new StringBuilder();
        boolean pendingWhitespace = false;
        boolean inString = false;
        boolean inCharacter = false;
        boolean escaped = false;
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            if (escaped) {
                result.append(character);
                escaped = false;
                continue;
            }
            if ((inString || inCharacter) && character == '\\') {
                result.append(character);
                escaped = true;
                continue;
            }
            if (!inCharacter && character == '"') {
                if (pendingWhitespace && result.length() > 0) {
                    result.append(' ');
                }
                pendingWhitespace = false;
                result.append(character);
                inString = !inString;
                continue;
            }
            if (!inString && character == '\'') {
                if (pendingWhitespace && result.length() > 0) {
                    result.append(' ');
                }
                pendingWhitespace = false;
                result.append(character);
                inCharacter = !inCharacter;
                continue;
            }
            if (!inString && !inCharacter && Character.isWhitespace(character)) {
                pendingWhitespace = result.length() > 0;
                continue;
            }
            if (pendingWhitespace && result.length() > 0) {
                result.append(' ');
            }
            pendingWhitespace = false;
            result.append(character);
        }
        return result.toString().trim();
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(bytes.length * 2);
            for (byte item : bytes) {
                result.append(String.format(Locale.ROOT, "%02x", item & 0xff));
            }
            return result.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static <K, V> Map<K, V> linkedMap() {
        return new LinkedHashMap<>();
    }

    private static final class Json {
        private Json() {
        }

        static String encode(Object value) {
            StringBuilder result = new StringBuilder();
            append(result, value);
            return result.toString();
        }

        private static void append(StringBuilder result, Object value) {
            if (value == null) {
                result.append("null");
            } else if (value instanceof String || value instanceof Character) {
                appendString(result, String.valueOf(value));
            } else if (value instanceof Number || value instanceof Boolean) {
                result.append(value);
            } else if (value instanceof Map<?, ?>) {
                result.append('{');
                boolean first = true;
                for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                    if (!first) {
                        result.append(',');
                    }
                    first = false;
                    appendString(result, String.valueOf(entry.getKey()));
                    result.append(':');
                    append(result, entry.getValue());
                }
                result.append('}');
            } else if (value instanceof Iterable<?>) {
                result.append('[');
                boolean first = true;
                for (Object item : (Iterable<?>) value) {
                    if (!first) {
                        result.append(',');
                    }
                    first = false;
                    append(result, item);
                }
                result.append(']');
            } else if (value.getClass().isArray()) {
                result.append('[');
                int length = java.lang.reflect.Array.getLength(value);
                for (int index = 0; index < length; index++) {
                    if (index > 0) {
                        result.append(',');
                    }
                    append(result, java.lang.reflect.Array.get(value, index));
                }
                result.append(']');
            } else {
                appendString(result, String.valueOf(value));
            }
        }

        private static void appendString(StringBuilder result, String value) {
            result.append('"');
            for (int index = 0; index < value.length(); index++) {
                char character = value.charAt(index);
                switch (character) {
                    case '"':
                        result.append("\\\"");
                        break;
                    case '\\':
                        result.append("\\\\");
                        break;
                    case '\b':
                        result.append("\\b");
                        break;
                    case '\f':
                        result.append("\\f");
                        break;
                    case '\n':
                        result.append("\\n");
                        break;
                    case '\r':
                        result.append("\\r");
                        break;
                    case '\t':
                        result.append("\\t");
                        break;
                    default:
                        if (character < 0x20) {
                            result.append(String.format(Locale.ROOT, "\\u%04x", (int) character));
                        } else {
                            result.append(character);
                        }
                }
            }
            result.append('"');
        }
    }
}
