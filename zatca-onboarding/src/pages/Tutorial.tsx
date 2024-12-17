import { useAppDispatch } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { Button, Carousel, Typography } from "antd";
import React from "react";

const Tutorial: React.FC = () => {
  const dispatch = useAppDispatch();

  const items = [
    {
      id: 1,
      src: "https://fakeimg.pl/1320x600/cccfd4/000000?text=1&font=bebas",
    },
    {
      id: 2,
      src: "https://fakeimg.pl/1320x600/cccfd4/000000?text=2&font=bebas",
    },
    {
      id: 3,
      src: "https://fakeimg.pl/1320x600/cccfd4/000000?text=3&font=bebas",
    },
    {
      id: 4,
      src: "https://fakeimg.pl/1320x600/cccfd4/000000?text=4&font=bebas",
    },
  ];

  const onOk = () => {
    dispatch(setCurrentPage(2));
  };

  return (
    <>
      <Carousel autoplay>
        {items.map((item, index) => (
          <div key={index}>
            <img src={item.src} alt={item.id.toString()} />
          </div>
        ))}
      </Carousel>
      {/* Center the button vertically and horizontally */}
      <div className="flex flex-col gap-2 bg-transparent justify-center items-center h-full">
        <Button
          className="w-1/3 p-6 bg-[#483f61] text-white font-bold"
          onClick={onOk}
        >
          Let's Get Started!!!
        </Button>
        <Typography.Text className="text-red-500">
          Continuing Means That You Agree To Our Terms Aand Conditions
        </Typography.Text>
      </div>
    </>
  );
};

export default Tutorial;
