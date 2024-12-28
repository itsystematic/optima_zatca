import { useAppDispatch } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { Button, Carousel, Flex, Typography } from "antd";
import React, { useRef, useState } from "react";

const Tutorial: React.FC = () => {
  const dispatch = useAppDispatch();
  const carouselRef = useRef(null);
  const [currentIndex, setCurrentIndex] = useState<number>(0);

  const items = [
    {
      id: 1,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/1.png" : "1.png",
    },
    {
      id: 2,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/2.png" : "2.png",
    },
    {
      id: 3,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/3.png" : "3.png",
    },
    {
      id: 4,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/4.png" : "4.png",
    },
    {
      id: 5,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/5.png" : "5.png",
    },
    {
      id: 6,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/6.png" : "6.png",
    },
    {
      id: 7,
      src: !isDev ? "/assets/optima_zatca/zatca-onboarding/7.png" : "7.png",
    },
  ];

  const handleNext = (skip? : boolean)=> {
    if (skip) {
      //@ts-ignore
      carouselRef.current?.goTo(items.length - 1);
      setCurrentIndex(items.length - 1);
      return;
    }
    if (isLastIndex) {
      onOk();
      return;
    }
    if (carouselRef.current) {    
      // @ts-ignore
      carouselRef.current.next();
    }
  };


  const handleAfterChange = (current: number) => {
    setCurrentIndex(current);
  };

  const onOk = () => {
    dispatch(setCurrentPage(2));
  };

  const isLastIndex = currentIndex === items.length - 1;


  return (
    <Flex vertical justify="space-between" className="h-[96%]">
      <Carousel afterChange={handleAfterChange} ref={carouselRef}>
        {items.map((item, index) => (
          <div key={index}>
            <img src={item.src} alt={item.id.toString()} />
          </div>
        ))}
      </Carousel>
      {/* Center the button vertically and horizontally */}
      <div className="flex flex-col gap-2 bg-transparent justify-center items-center">
        <Button
        type="primary"
          className={` ${isLastIndex && 'bg-[#39b54a]'} w-1/3 p-6 font-bold`}
          onClick={() => handleNext()}
        >
          {isLastIndex ? __("Get Started") : __("Next")}
        </Button>
        <Button type="default" className={`${isLastIndex && 'hidden'} w-1/3 p-6 font-bold`} onClick={() => handleNext(true)}>
          {__("Skip")}
        </Button>
        <Typography.Text className="text-red-700">
          {__("Continuing Means That You Agree To Our Terms Aand Conditions")}
        </Typography.Text>
      </div>
    </Flex>
  );
};

export default Tutorial;
