<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gráfico interactivo con PHP</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN" crossorigin="anonymous">
    <style>
        /* Estilos personalizados */
        body {
            padding-top: 20px;
        }
    </style>
</head>

<body>
    <?php
    $filename = 'grafico_curvas_plotly.html';
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Recuperar la cédula del formulario
        $cedula = isset($_POST['cedula']) ? $_POST['cedula'] : '';
    }

    // Ejecutar el script de Python al cargar la página
    //exec("python curvas_de_crecimiento.py $cedula", $output, $return_var);
    exec(".\\venv\\Scripts\\python.exe curvas_de_crecimiento.py $cedula", $output, $return_var);

    // Verificar si la ejecución fue exitosa
    if ($return_var === 0) {
        // Obtener el contenido HTML renderizado
        $htmlContent = file_get_contents($filename);

        // Mostrar el contenido HTML dentro de un iframe
        echo '<iframe srcdoc="' . htmlspecialchars($htmlContent) . '" width="100%" height="700px"></iframe>';
    } else {
        echo 'Error al ejecutar el script de Python.';
    }
    ?>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL" crossorigin="anonymous"></script>
</body>

</html>