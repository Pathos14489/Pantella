console.log("Loading openai_api settings...");
// All the settings here are the defaults, this is just included as an example of how it WOULD work to add custom settings javascript for the front end. The folder structure and filename is IMPORTANT. You must put this file in a folder with the same name as your inference engine, and the filename must be settings.js. So for example, for an inference engine with the slug "my_inference_engine", you would put this file at ./inference_engines/my_inference_engine/settings.js in your addon templates directory. If you don't follow this structure, your custom settings won't be included in the UI.
let openai_api_inferenceSettings = {{inference_engines.inference_engines["openai_api"]|tojson}};
let openai_api_tabContent = document.createElement("div");
openai_api_tabContent.id = "inference_openai_api_settings";
openai_api_tabContent.className = "tab_content";
let openai_api_header = document.createElement("h3");
openai_api_header.textContent = `{{inference_engine}} - Settings`;
openai_api_tabContent.appendChild(openai_api_header);
openai_api_tabContent.appendChild(document.createElement("br"));
let openai_api_description = document.createElement("p");
openai_api_description.textContent = openai_api_inferenceSettings.description || "No description available for this inference engine.";
openai_api_tabContent.appendChild(openai_api_description);
openai_api_tabContent.appendChild(document.createElement("br"));
for (property in openai_api_inferenceSettings.default_settings) {
    let defaultSetting = openai_api_inferenceSettings.default_settings[property];
    let settingsDescription = openai_api_inferenceSettings.settings_description[property]
    let settingOptions = openai_api_inferenceSettings.options[property];
    console.log("Processing property:", property, "with value:", defaultSetting);
    const label = document.createElement("label");
    label.innerHTML = `<h4>${property}:</h4>`;
    let exampleOptions = {
        "openai_completions_type": [
            {
                "name": "Text Completions",
                "value": "text",
                "description": "Use text completions for the OpenAI API. This is the default and recommended option for most models.",
                "default": true,
                "disabled": false
            },
            {
                "name": "Chat Completions",
                "value": "chat",
                "description": "Use chat completions for the OpenAI API. This is recommended for models that support chat completions, such as GPT-3.5 Turbo and GPT-4.",
                "default": false,
                "disabled": false
            }
        ]
    }
    let input;
    if (settingOptions && settingOptions.length > 0){
        console.log("Property has options:", property, settingOptions);
        input = document.createElement("select");
        input.id = `inference_openai_api__${property}`;
        settingOptions.forEach(option => {
            const opt = document.createElement("option");
            opt.value = option.value;
            opt.textContent = option.name;
            if (option.default) {
                opt.selected = true;
            }
            if (option.disabled) {
                opt.disabled = true;
            }
            if (option.description) {
                opt.title = option.description; // Add description as tooltip
            }
            input.appendChild(opt);
        });
    }else{
        input = document.createElement("input");
        input.id = `inference_openai_api__${property}`;
        switch (typeof defaultSetting) {
            case "boolean":
                console.log("Property is boolean:", property, defaultSetting);
                input.type = "checkbox";
                input.checked = defaultSetting;
                break;
            case "number":
                console.log("Property is number:", property, defaultSetting);
                input.type = "number";
                input.value = defaultSetting;
                break;
            case "string":
                console.log("Property is string:", property, defaultSetting);
                input.type = "text";
                input.value = defaultSetting;
                break;
            default:
                console.log("Property is of unknown type:", property, defaultSetting);
                input.type = "text";
                input.value = JSON.stringify(defaultSetting);
        }
        input.placeholder = `Enter ${property} here`;
    }
    openai_api_tabContent.appendChild(label);
    if (settingsDescription.length > 0) {
        let descriptionText = document.createElement("p");
        descriptionText.textContent = settingsDescription;
        openai_api_tabContent.appendChild(descriptionText);
    }
    openai_api_tabContent.appendChild(input);
    if (typeof defaultSetting == "boolean") {
        openai_api_tabContent.appendChild(document.createElement("br"));
    }
}
inferenceEditorTabs.appendChild(openai_api_tabContent);
let openai_api_button = document.createElement("button");
openai_api_button.id = `inference_openai_api__settings_button`;
openai_api_button.textContent = `{{inference_engine}}`;
openai_api_button.onclick = function() {
    let allTabs = inferenceEditorTabs.querySelectorAll(".tab_content");
    allTabs.forEach(tab => tab.classList.remove("active"));
    let allButtons = inferenceEditorTabButtons.querySelectorAll("button");
    allButtons.forEach(btn => btn.classList.remove("active"));
    openai_api_tabContent.classList.add("active");
    this.classList.add("active");
};
inferenceEditorTabButtons.appendChild(openai_api_button);
if (openai_api_inferenceSettings.loaded) {
    openai_api_tabContent.classList.add("active");
    openai_api_button.classList.add("active");
}