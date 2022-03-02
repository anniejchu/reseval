import React, { useState } from 'react';

import '../css/components.css';

export default function Text({ src }) {
    /* Create a textbox */
    const [text, setText] = useState(undefined);

    // Get text
    fetch(src)
        .then(response => response.text())
        .then(response => setText(response));

    // Render
    if (typeof text === 'undefined') { return null; }
    return (
        <div
            style={{
                color: 'black',
                justifyContent: 'center',
                display: 'flex',
                width: '90%'
            }}
        >
            {text}
        </div>);
};
