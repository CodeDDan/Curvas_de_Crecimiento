<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gráfico interactivo con PHP</title>
</head>

<body>
    <h1>Resultado del gráfico</h1>

    <?php
    $filename = 'grafico_curvas_plotly.html';

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Recuperar la cédula del formulario
        $cedula = isset($_POST['cedula']) ? $_POST['cedula'] : '';
    }

    // Ejecutar el script de Python al cargar la página
    exec("python curvas_de_crecimiento.py $cedula", $output, $return_var);

    // Verificar si la ejecución fue exitosa
    if ($return_var === 0) {
        // Obtener el contenido HTML renderizado
        $htmlContent = file_get_contents($filename);

        // Mostrar el contenido HTML dentro de un iframe
        echo '<iframe srcdoc="' . htmlspecialchars($htmlContent) . '" width="100%" height="600px"></iframe>';
    } else {
        echo 'Error al ejecutar el script de Python.';
    }
    ?>

</body>

</html>