import React, { useState, useEffect } from "react";
import { Header, Icon, Menu, Segment, Sidebar } from "semantic-ui-react";
import Gallery from "react-grid-gallery";
import Histogram from "./Histogram";

const GalleryWrapper = (props) => (
  <div style={{ overflowY: "auto" }}>
    <Gallery enableImageSelection={false} {...props} />
  </div>
);

export default function Overview() {
  const [tab, setTab] = useState("overview");
  const [images, setImages] = useState([]);

  useEffect(() => {
    (async () => {
      const server = "http://localhost:5101/";
      let res = await fetch(server);
      res = await res.json();
      const labels = Object.fromEntries(
        await Promise.all(
          res
            .filter((filename) => filename.endsWith(".json"))
            .map(async (filename) => {
              const res = await fetch(server + filename);
              return [parseInt(filename), await res.json()];
            })
        )
      );
      setImages(
        res
          .filter((filename) => filename.endsWith(".png"))
          .map((filename) => ({
            src: server + filename,
            thumbnail: server + filename,
            tags: labels[parseInt(filename)].objects.objects.map((obj) => ({
              value: obj.label,
            })),
          }))
      );
    })();
  }, []);

  const tags = Array.from(
    new Set(
      images.reduce(
        (arr, image) => arr.concat(image.tags.map((tag) => tag.value)),
        []
      )
    )
  );

  let content;
  if (tab == "overview") {
    const data = tags
      .map((tagName) => ({
        name: tagName,
        count: images.filter((img) =>
          img.tags.some((tag) => tag.value == tagName)
        ).length,
      }))
      .sort((a, b) => b.count - a.count);

    content = (
      <Segment>
        <Histogram data={data} />
      </Segment>
    );
  } else if (tab == "pools") {
    content = (
      <>
        {tags.map((tagName) => (
          <React.Fragment key={tagName}>
            <h3>{tagName}</h3>
            <GalleryWrapper
              images={images.filter(
                (image) =>
                  image.tags.filter((tag) => tag.value === tagName).length
              )}
            />
          </React.Fragment>
        ))}
      </>
    );
  } else {
    content = <GalleryWrapper images={images} />;
  }

  return (
    <Segment>
      <Header as="h3">Overview: [name]</Header>

      <Menu pointing secondary>
        {["overview", "pools", "side-by-side", "overlayed"].map((item) => (
          <Menu.Item
            key={item}
            name={item}
            active={tab === item}
            onClick={() => setTab(item)}
          />
        ))}
      </Menu>

      {content}
    </Segment>
  );
}
